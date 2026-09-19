"""Sealed Native numerical mechanism validation; creates no role data or optimizer."""
from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path
import time

from rwkv_lh import statetune_core as core
from rwkv_lh.statetune_native_runtime import (
    verify_native_runtime, load_native_runtime, verify_loaded_libraries,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--runtime-sha256', required=True)
    parser.add_argument('--registration', type=Path, required=True)
    parser.add_argument('--registration-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    registration = core.read_sealed_json(args.registration, args.registration_sha256)
    core.require(registration['purpose'] == 'numerical_mechanism_only' and registration['optimizer_steps'] == 0,
                 'this validator cannot train or generate role samples')
    started = time.monotonic()
    args.output.mkdir(parents=True, exist_ok=False)
    report = {'registration_sha256': args.registration_sha256, 'runtime_sha256': args.runtime_sha256,
              'optimizer_steps': 0, 'role_samples': 0, 'stages': [], 'passed': False}

    def record(stage, **values):
        report['stages'].append({'stage': stage, **values})
        report['elapsed_seconds'] = time.monotonic() - started
        (args.output / 'RESULT.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report['stages'][-1]), flush=True)
        core.require(report['elapsed_seconds'] <= registration['max_seconds'], 'numerical validation budget exhausted')

    try:
        root = Path(__file__).resolve().parents[1]
        runtime = verify_native_runtime(args.runtime, args.runtime_sha256, source_root=root,
            source_manifest_sha256=registration['source_manifest_sha256'])
        load_native_runtime(runtime)
        import torch
        from rwkv_lh.statetune_native_model import build
        from rwkv_lh.inference.vllm_rwkv import PersistentVLLMRWKVExtractor
        from rwkv_lh.inference.vllm_rwkv_state_profiles_v1 import (
            RWKV7InitialStateProfiles, RWKV7_STATE_PROFILE_MANIFEST_SCHEMA,
        )
        core.require(torch.cuda.device_count() == 1, 'validation requires one visible registered GPU')
        core.require(core.device_uuid_matches(str(torch.cuda.get_device_properties(0).uuid), registration['gpu_uuid']),
                     'validation GPU identity differs')
        artifact = Path(runtime['model_artifact']['path'])
        manifest = core.read_sealed_json(artifact / 'manifest.json', runtime['model_artifact']['manifest_sha256'])
        core.require(manifest['source']['sha256'] == registration['base_sha256'], 'registered base differs')
        core.verify_file(artifact / 'model.safetensors', manifest['output']['weights_sha256'])
        core.verify_file(artifact / 'rwkv_vocab_v20230424.txt', manifest['output']['vocab_sha256'])
        spec = {'model_artifact': str(artifact), 'context_tokens': registration['context_tokens'],
                'base': {'path': manifest['source']['path'], 'sha256': registration['base_sha256']}}
        record('identity_admitted', gpu_uuid=registration['gpu_uuid'])
        model = build(spec)
        params = core.state_parameters(model, layers=model.layout.layers)
        serving = PersistentVLLMRWKVExtractor._load_direct_model(artifact)
        core.require(str(serving.wkv_state_dtype) == 'torch.float32', 'serving State arithmetic differs')
        from vllm.tokenizers.rwkv import RWKVTokenizer
        tokenizer = RWKVTokenizer.from_pretrained(artifact)
        record('models_loaded', layout=vars(model.layout), state_shape=list(model.layout.portable_state_shape),
               tokenizer_vocab_size=int(tokenizer.vocab_size), bos_token_id=int(tokenizer.bos_token_id))
        generator = torch.Generator(device='cpu').manual_seed(registration['state_seed'])
        portable = {name: (torch.randn(value.shape, generator=generator) * registration['state_scale']).bfloat16()
                    for name, value in params.items()}
        state_path = args.output / 'mechanism_state.pth'
        torch.save(portable, state_path)
        profile_path = args.output / 'STATE_PROFILES.json'
        profile_path.write_text(json.dumps({'schema_version': RWKV7_STATE_PROFILE_MANIFEST_SCHEMA,
            'model_artifact': str(artifact), 'model_revision': runtime['engine']['revision'], 'default_profile': 'zero',
            'profiles': [{'id': 'mechanism', 'format': 'rwkv-peft-time-state.v1', 'path': str(state_path.resolve()),
                          'sha256': core.sha256_file(state_path)}]}, indent=2) + '\n')
        profiles = RWKV7InitialStateProfiles.load(str(profile_path), core.sha256_file(profile_path),
            model_artifact=str(artifact), model_revision=runtime['engine']['revision'], total_num_layers=model.layout.layers,
            total_num_heads=model.layout.heads, layer_offset=0, num_layers=model.layout.layers, tp_size=1, tp_rank=0,
            num_heads=model.layout.heads, head_size=model.layout.head_size, device=torch.device('cuda:0'), dtype=torch.float32)

        def set_state(nonzero):
            with torch.no_grad():
                for name, parameter in params.items():
                    parameter.copy_(portable[name] if nonzero else torch.zeros_like(parameter))

        def tokens_for(length):
            # Fixed numerical token pattern, independent of task text or expected role outputs.
            values = (torch.arange(length, device='cuda:0', dtype=torch.long) * 37 + 101) % model.layout.vocab
            values[0] = tokenizer.bos_token_id
            return values.unsqueeze(0)

        for nonzero in (False, True):
            set_state(nonzero)
            for length in registration['alignment_lengths']:
                tokens = tokens_for(length)
                with torch.inference_mode():
                    recurrent = serving.zero_state(1)
                    if nonzero:
                        recurrent[1].copy_(profiles.resolve('mechanism').wkv_state.unsqueeze(1))
                    reference = serving.forward_all_logits(tokens, recurrent)
                    actual = model(tokens)
                    core.require(actual.shape == reference.shape and bool(torch.isfinite(actual).all())
                                 and bool(torch.isfinite(reference).all()), 'alignment logit geometry or finiteness differs')
                    max_error = float((actual - reference).abs().max())
                    core.require(max_error <= registration['max_logit_error'], 'serving/training logits differ')
                    record('all_vocab_alignment', state='nonzero' if nonzero else 'zero', tokens=length,
                           compared_logits=actual.numel(), max_absolute_error=max_error)
                    del actual, reference, recurrent
        del serving
        gc.collect()
        torch.cuda.empty_cache()
        set_state(True)
        frozen = {name: parameter._version for name, parameter in model.named_parameters() if name not in params}
        initial = {name: p.detach().clone() for name, p in params.items()}
        for length in registration['backward_lengths']:
            torch.cuda.reset_peak_memory_stats()
            model.zero_grad(set_to_none=True)
            tokens = tokens_for(length)
            logits = model(tokens)
            logits.retain_grad()
            labels = torch.full_like(tokens, -100)
            target_start = length - min(4, length)
            labels[:, target_start:] = (tokens[:, target_start:] + 1) % model.layout.vocab
            loss = core.target_cross_entropy(logits, labels)
            core.require(bool(torch.isfinite(loss)), 'target CE is nonfinite')
            loss.backward()
            gradients = {name: {'finite': p.grad is not None and bool(torch.isfinite(p.grad).all()),
                               'nonzero': p.grad is not None and bool(torch.count_nonzero(p.grad))}
                         for name, p in params.items()}
            core.require(all(row['finite'] and row['nonzero'] for row in gradients.values()), 'State gradient is absent or invalid')
            core.require(torch.count_nonzero(logits.grad[:, :target_start]).item() == 0, 'prompt logits received direct loss gradient')
            core.require(all(not p.requires_grad and p.grad is None and p._version == frozen[name]
                             for name, p in model.named_parameters() if name in frozen), 'frozen base was trained or mutated')
            core.require(all(torch.equal(p.detach(), initial[name]) for name, p in params.items()), 'forward/backward mutated initial State')
            peak = torch.cuda.max_memory_allocated()
            core.require(peak <= registration['max_allocated_bytes'], 'registered GPU memory budget exceeded')
            record('full_model_backward', tokens=length, loss=float(loss.detach()), gradients=gradients,
                   prompt_loss_gradient_zero=True, base_unchanged=True, state_unchanged=True, peak_allocated_bytes=peak)
            del logits, loss
            model.zero_grad(set_to_none=True)
        with torch.inference_mode():
            tokens = tokens_for(17)
            first = model(tokens)
            second = model(tokens)
            core.require(torch.equal(first, second), 'independent samples leak recurrent State')
        verify_loaded_libraries(runtime)
        report['passed'] = True
        record('complete', independent_samples_equal=True, binary_inventory_verified=True)
    except Exception as exc:
        report['error'] = {'type': type(exc).__name__, 'message': str(exc)}
        report['elapsed_seconds'] = time.monotonic() - started
        (args.output / 'RESULT.json').write_text(json.dumps(report, indent=2) + '\n')
        raise
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
