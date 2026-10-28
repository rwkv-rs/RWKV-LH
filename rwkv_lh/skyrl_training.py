"""Frozen data handoff to SkyRL's native SFT trainer; no local optimizer.

Tokenization, target selection and provenance remain owned by the production
data pipeline. SkyRL owns gradients, recurrent chunks, optimizer checkpoints,
resume and Transformers-format exports. Preparing a handoff never trains.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile

from .inference.uploaded_sources import ENGINE_SCHEMA, verify_manifest

RUN_SCHEMA = 'rwkv-lh.skyrl-sft-run.v1'
STORE_SCHEMA = 'rwkv-lh.skyrl-token-store.v1'
GPUS = {0: 'GPU-1faf7f09-25f4-2515-b707-6e0766aa841d',
        1: 'GPU-3e07b500-7d09-ce83-cc1a-35c6b13f8863'}
LOCK = json.loads(Path(__file__).with_name('skyrl.lock.json').read_text())


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def sealed(reference):
    path = Path(reference['path']).resolve(strict=True)
    if not path.is_file() or sha(path) != reference['sha256']:
        raise ValueError('sealed file identity differs: ' + str(path))
    return json.loads(path.read_text())


def gpu_uuid(index):
    if type(index) is not int or index not in GPUS:
        raise ValueError('only registered GPU 0 or GPU 1 is permitted')
    return GPUS[index]


BPTT_PROBE = '''
import json
import torch
from transformers.models.rwkv.configuration_rwkv import RwkvConfig
from transformers.models.rwkv.modeling_rwkv import RwkvCache

config = RwkvConfig(architecture_version='rwkv7', hidden_size=64, num_hidden_layers=1,
                    intermediate_size=256, head_size=64, num_attention_heads=1, context_length=16)
cache = RwkvCache(config)
layer = cache.layers[0]
leaf = torch.zeros(1, 1, 64, 64, dtype=torch.float32, requires_grad=True)
boundary = leaf * 2
if boundary.grad_fn is None:
    raise SystemExit('probe boundary tensor is not differentiable')
layer.recurrent_states[0] = boundary
layer.is_recurrent_states_initialized[0] = True
cloned = cache.clone().layers[0].recurrent_states[0]
if cloned is None:
    raise SystemExit('clone dropped the recurrent state')
if cloned.grad_fn is not None:
    cloned.sum().backward()
detached = cache.detach().layers[0].recurrent_states[0]
print(json.dumps({
    'clone_preserves_graph': cloned.grad_fn is not None,
    'gradient_reaches_leaf': leaf.grad is not None and bool(leaf.grad.abs().sum() > 0),
    'detach_breaks_graph': detached is not None and detached.grad_fn is None,
    'torch': torch.__version__,
}))
'''


def verify_chunk_gradient(python, source_root):
    """SkyRL carries chunk boundaries by RwkvCache.clone(); a detaching clone
    silently turns exact BPTT into truncated BPTT while loss still falls."""
    process = subprocess.run(['uv', 'run', '--isolated', '--no-project', str(python), '-c', BPTT_PROBE],
                             cwd=source_root, capture_output=True, text=True, check=False)
    if process.returncode != 0:
        raise ValueError('cross-chunk gradient probe failed to run: ' + process.stderr.strip()[-2000:])
    try:
        observed = json.loads(process.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        raise ValueError('cross-chunk gradient probe returned no verdict: ' + process.stdout.strip()[-2000:])
    required = ('clone_preserves_graph', 'gradient_reaches_leaf', 'detach_breaks_graph')
    if any(observed.get(key) is not True for key in required):
        raise ValueError('pinned RwkvCache does not carry gradients across chunk boundaries: '
                         + json.dumps(observed, sort_keys=True))
    return observed


def token_row(row):
    tokens = row['token_ids']
    spans, supervised = row['target_spans'], row['supervised']
    if (not isinstance(tokens, list) or len(tokens) < 2
            or any(type(v) is not int or v < 0 for v in tokens)
            or len(spans) != len(supervised)):
        raise ValueError('invalid complete episode tokens or supervision')
    mask, previous = [0] * len(tokens), 1
    for span, enabled in zip(spans, supervised):
        if (not isinstance(span, (list, tuple)) or len(span) != 2
                or any(type(v) is not int for v in span) or type(enabled) is not bool):
            raise ValueError('invalid target span')
        start, length = span
        if start < previous or length <= 0 or start + length > len(tokens):
            raise ValueError('overlapping, first-token or out-of-range target span')
        mask[start:start + length] = [int(enabled)] * length
        previous = start + length
    if not any(mask):
        raise ValueError('episode has no supervised next-token targets')
    return dict(input_ids=tokens, loss_mask=mask, episode_id=row['episode_id'],
                source=row.get('source', row.get('source_group')), input_protocol=row['input_protocol'])


def export_rows(rows, output, *, provenance):
    """Publish complete unshifted masks; SkyRL performs next-token alignment."""
    output = Path(output).absolute()
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    count = token_count = targets = 0
    ids = set()
    with tempfile.TemporaryDirectory(prefix='.skyrl-', dir=output.parent) as staging:
        staging = Path(staging)
        with (staging / 'train.jsonl').open('w') as stream:
            for source in rows:
                row = token_row(source)
                if row['episode_id'] in ids:
                    raise ValueError('duplicate source episode identity')
                ids.add(row['episode_id'])
                stream.write(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n')
                count += 1
                token_count += len(row['input_ids'])
                targets += sum(row['loss_mask'])
            stream.flush()
            os.fsync(stream.fileno())
        if not count:
            raise ValueError('empty SkyRL training store')
        result = dict(schema_version=STORE_SCHEMA, episodes=count, input_tokens=token_count,
                      supervised_tokens=targets, provenance=provenance,
                      train_file=dict(path='train.jsonl', sha256=sha(staging / 'train.jsonl')),
                      truncated_tokens=0, added_tokens=0)
        # Only train.jsonl is passed to SkyRL, never this metadata JSON.
        (staging / 'MANIFEST.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        os.rename(staging, output)
    return result


def native_config(*, model, train_file, output, batch_size, learning_rate, seed,
                  epochs, max_steps, chunk_size, checkpoint_interval, resume_from='',
                  cpu_offload=True):
    if (any(type(v) is not int or v <= 0 for v in
            (batch_size, epochs, max_steps, chunk_size, checkpoint_interval))
            or type(seed) is not int or not math.isfinite(learning_rate) or learning_rate <= 0):
        raise ValueError('explicit positive SkyRL training budget is required')
    output = Path(output).absolute()
    return {
        'strategy': 'fsdp', 'model.path': str(model), 'model.lora.rank': 0,
        'model_config_kwargs': {'wkv_mode': 'fp32io16'},
        'pretokenized_dataset_paths': [str(train_file)], 'max_length': None,
        'remove_microbatch_padding': False, 'use_sequence_packing': False,
        'rwkv_chunk_size': chunk_size, 'num_epochs': epochs, 'max_training_steps': max_steps,
        'batch_size': batch_size, 'micro_train_batch_size_per_gpu': 1,
        'placement.num_nodes': 1, 'placement.num_gpus_per_node': 1,
        'fsdp_config.fsdp_size': 1, 'fsdp_config.cpu_offload': cpu_offload,
        'fsdp_config.reshard_after_forward': False,
        'fsdp_config.sync_gradients_each_microbatch': cpu_offload,
        'fsdp_config.mixed_precision': {'param_dtype': 'bf16', 'reduce_dtype': 'fp32', 'buffer_dtype': 'fp32'},
        'optimizer_config.lr': learning_rate, 'optimizer_config.weight_decay': 0.0,
        'optimizer_config.max_grad_norm': 1.0, 'optimizer_config.scheduler': 'constant_with_warmup',
        'optimizer_config.num_warmup_steps': 0, 'optimizer_config.offload_after_step': False,
        'seed': seed, 'sampler': 'sequential', 'num_workers': 0,
        'dataloader_num_workers': 0, 'dataloader_persistent_workers': False,
        'async_batch_collation': False, 'ckpt_path': str(output / 'checkpoints'),
        'export_path': str(output / 'hf_exports'), 'ckpt_interval': checkpoint_interval,
        'hf_save_interval': checkpoint_interval, 'max_ckpts_to_keep': -1,
        'resume_from': str(resume_from), 'eval_before_train': False, 'eval_interval': 0,
        'eval_command': None, 'logger': 'console', 'project_name': 'rwkv-lh',
        'run_name': output.name, 'enable_ray_gpu_monitor': False,
    }


def command(python, configuration):
    return ['uv', 'run', '--isolated', '--no-project', str(python), '-m', 'skyrl.train.main_sft',
            *(key + '=' + json.dumps(value, ensure_ascii=False, separators=(',', ':'))
              for key, value in configuration.items())]


def validate_registration(registration):
    if registration.get('schema_version') != RUN_SCHEMA:
        raise ValueError('current SkyRL training registration is required')
    references = registration.get('authorization_references')
    if not isinstance(references, list) or not references:
        raise ValueError('explicit optimizer authorization references are required')
    for reference in references:
        authority = sealed(reference)
        if (authority.get('experiment') != registration.get('experiment')
                or authority.get('optimizer_steps') != registration.get('max_steps')
                or not authority.get('owner_instruction')):
            raise ValueError('optimizer authorization scope differs')
        bindings = {
            'method': registration.get('method'), 'epochs': registration.get('epochs'),
            'gpu_uuid': registration.get('gpu_uuid'),
            'model_manifest_sha256': registration.get('model_manifest', {}).get('sha256'),
            'dataset_manifest_sha256': registration.get('dataset', {}).get('sha256'),
            'skyrl_source_manifest_sha256': registration.get('skyrl_source', {}).get('sha256'),
        }
        if any(value is None or authority.get(key) != value for key, value in bindings.items()):
            raise ValueError('optimizer authorization model, data, source or resource binding differs')
    if registration.get('gpu_uuid') != gpu_uuid(registration['gpu_index']):
        raise ValueError('registered GPU identity differs')
    if registration.get('method') != 'sft_full':
        raise ValueError('this entrance uses native SkyRL full-parameter SFT')


def prepare(registration, output):
    validate_registration(registration)
    engine = registration['skyrl_source']
    verified = verify_manifest(Path(engine['path']), engine['sha256'], expected_schema=ENGINE_SCHEMA,
                               expected_revision=LOCK['revision'])
    root = Path(verified['root'])
    if not (root / 'skyrl/train/main_sft.py').is_file():
        raise ValueError('SkyRL native SFT source is missing')
    chunk_gradient = verify_chunk_gradient(registration['python'], root)
    model = sealed(registration['model_manifest'])
    from .inference.irwkv_artifact import verify_artifact, verify_vocabulary
    artifact = verify_artifact(Path(model['root']), expected_manifest=registration['model_manifest'])
    from .token_budget import VOCAB_PATH
    verify_vocabulary(model['root'], VOCAB_PATH)
    dataset = registration['dataset']
    if dataset.get('format') == 'ccview_episodes':
        from .cc_view_training_freeze import load_split
        rows, manifest = load_split(dataset['path'], dataset['sha256'], 'train',
                                    context_tokens=registration['data_context_tokens'])
    elif dataset.get('format') == 'executor_episodes':
        from .statetune_episodes import load_split
        cfg = json.loads((Path(model['root'])/'config.json').read_text())
        manifest, rows = load_split(Path(dataset['path']), dataset['sha256'], 'train.jsonl',
            context_tokens=registration['data_context_tokens'], vocab_size=cfg['vocab_size'],
            bos_token_id=cfg['bos_token_id'], model_sha256=artifact['source']['sha256'],
            tokenizer_sha256=artifact['source_vocabulary_sha256'])
    else:
        raise ValueError('registration must select ccview_episodes or executor_episodes')
    if manifest['tokenizer_sha256'] != artifact['source_vocabulary_sha256']:
        raise ValueError('frozen dataset and model vocabulary identities differ')
    if manifest['model_sha256'] != artifact['source']['sha256']:
        raise ValueError('frozen dataset and model source identities differ')
    output = Path(output).absolute()
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    exported = export_rows(rows, output / 'tokens', provenance=dataset)
    config = native_config(model=model['root'], train_file=str(output / 'tokens/train.jsonl'),
        output=output, batch_size=registration['batch_size'], learning_rate=registration['learning_rate'],
        seed=registration['seed'], epochs=registration['epochs'], max_steps=registration['max_steps'],
        chunk_size=registration['chunk_size'], checkpoint_interval=registration['checkpoint_interval'],
        resume_from=registration.get('resume_from', ''), cpu_offload=registration.get('cpu_offload', True))
    result = dict(schema_version=RUN_SCHEMA, configuration=config, dataset=exported,
                  model_manifest=registration['model_manifest'], chunk_gradient=chunk_gradient,
                  command=command(registration['python'], config), source_root=str(root),
                  training_started=False, optimizer_steps=0)
    (output / 'PREPARED.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    return result


def run(registration, output):
    prepared = prepare(registration, output)
    expected = gpu_uuid(registration['gpu_index'])
    actual = subprocess.check_output(['nvidia-smi', '--query-gpu=uuid', '--format=csv,noheader',
                                     '-i', str(registration['gpu_index'])], text=True).strip()
    if actual != expected:
        raise ValueError('physical GPU UUID differs; no training started')
    env = dict(os.environ, CUDA_VISIBLE_DEVICES=expected, RAY_ADDRESS='local')
    env.pop('PYTHONPATH', None)
    with (Path(output) / 'skyrl.log').open('xb') as log:
        process = subprocess.run(prepared['command'], cwd=prepared['source_root'], env=env,
                                 stdout=log, stderr=subprocess.STDOUT, check=False)
    result = dict(at=datetime.now(timezone.utc).isoformat(), exit_code=process.returncode,
                  trainer='skyrl.train.main_sft', log_sha256=sha(Path(output) / 'skyrl.log'),
                  status='trainer_exited' if process.returncode == 0 else 'trainer_failed',
                  product_adopted=False)
    # Exit status does not invent optimizer counts or qualify the resulting model.
    (Path(output) / 'RESULT.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registration', required=True)
    parser.add_argument('--registration-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--execute', action='store_true', help='Run the explicitly authorized optimizer budget')
    args = parser.parse_args()
    registration = sealed(dict(path=args.registration, sha256=args.registration_sha256))
    result = (run if args.execute else prepare)(registration, args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(result.get('exit_code', 0) != 0)


if __name__ == '__main__':
    raise SystemExit(main())
