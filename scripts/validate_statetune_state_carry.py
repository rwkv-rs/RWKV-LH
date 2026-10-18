"""Sealed chunked State-carry numerical validation; creates no role data or optimizer.

1. Alignment: every chunk's all-vocabulary training logits and carried State
   equal serving that keeps one persistent recurrent State across the same
   chunks (zero and registered nonzero initial State).
2. Gradient: chunked backward with carried State matches one full-sequence
   backward of the same targets, with a chunk that has no targets.
3. Long backward: an episode longer than the context trains chunk by chunk
   within the memory budget and recomputes every boundary State bitwise.
"""
from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path
import time

from rwkv_lh import statetune_core as core
from rwkv_lh.statetune_native_validation import validate_carry_plan
from rwkv_lh.statetune_native_runtime import (
    verify_native_runtime, load_native_runtime, verify_loaded_libraries,
)


def chunk_sizes(row):
    starts = row['chunk_starts']
    return [b - a for a, b in zip(starts, [*starts[1:], row['tokens']])]


def target_spans(row):
    """Last four label positions of every even chunk; odd chunks carry State without targets."""
    spans = []
    for index, (start, size) in enumerate(zip(row['chunk_starts'], chunk_sizes(row))):
        if index % 2 == 0:
            count = min(4, size)
            spans.append([start + size - count + 1, count])
    return spans


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--runtime-sha256', required=True)
    parser.add_argument('--registration', type=Path, required=True)
    parser.add_argument('--registration-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    registration = core.read_sealed_json(args.registration, args.registration_sha256)
    validate_carry_plan(registration)
    started = time.monotonic()
    args.output.mkdir(parents=True, exist_ok=False)
    report = {'registration_sha256': args.registration_sha256, 'runtime_sha256': args.runtime_sha256,
              'optimizer_steps': 0, 'role_samples': 0, 'stages': [], 'passed': False}

    def record(stage, **values):
        report['stages'].append({'stage': stage, **values})
        report['elapsed_seconds'] = time.monotonic() - started
        core.require(report['elapsed_seconds'] <= registration['max_seconds'], 'numerical validation budget exhausted')
        if stage == 'complete':
            report['passed'] = True
        (args.output / 'RESULT.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report['stages'][-1]), flush=True)

    try:
        root = Path(__file__).resolve().parents[1]
        runtime = verify_native_runtime(args.runtime, args.runtime_sha256, source_root=root,
            source_manifest_sha256=registration['source_manifest_sha256'])
        load_native_runtime(runtime)
        import torch
        from rwkv_lh.statetune_native_model import build
        from rwkv_lh.statetune_state_carry import episode_chunks, state_carry_backward
        from rwkv_lh.inference.vllm_rwkv import PersistentVLLMRWKVExtractor
        from rwkv_lh.inference.vllm_rwkv_state_profiles_v1 import (
            RWKV7InitialStateProfiles, RWKV7_STATE_PROFILE_MANIFEST_SCHEMA,
        )
        from vllm.tokenizers.rwkv import RWKVTokenizer
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
        names = list(params)
        serving = PersistentVLLMRWKVExtractor._load_direct_model(artifact)
        core.require(str(serving.wkv_state_dtype) == 'torch.float32', 'serving State arithmetic differs')
        tokenizer = RWKVTokenizer.from_pretrained(artifact)
        record('models_loaded', layout=vars(model.layout), bos_token_id=int(tokenizer.bos_token_id))
        generator = torch.Generator(device='cpu').manual_seed(registration['state_seed'])
        # Round through BF16 like a published portable State.
        portable = {name: (torch.randn(value.shape, generator=generator) * registration['state_scale']).bfloat16()
                    for name, value in params.items()}
        core.require(all(bool(torch.isfinite(value).all()) and bool(torch.count_nonzero(value))
                         for value in portable.values()),
                     'registered nonzero State must remain finite and nonzero in every layer after conversion')
        state_path = args.output / 'mechanism_state.pth'
        torch.save(portable, state_path)
        profile_path = args.output / 'STATE_PROFILES.json'
        profile_path.write_text(json.dumps({'schema_version': RWKV7_STATE_PROFILE_MANIFEST_SCHEMA,
            'model_artifact': str(artifact), 'model_revision': runtime['engine']['revision'], 'default_profile': 'zero',
            'profiles': [{'id': 'mechanism', 'format': 'rwkv-peft-time-state.v1', 'path': str(state_path.resolve()),
                          'sha256': core.sha256_file(state_path)}]}, indent=2) + '\n')
        # The serving loader, not this script, decides the portable-to-recurrent layout.
        profiles = RWKV7InitialStateProfiles.load(str(profile_path), core.sha256_file(profile_path),
            model_artifact=str(artifact), model_revision=runtime['engine']['revision'], total_num_layers=model.layout.layers,
            total_num_heads=model.layout.heads, layer_offset=0, num_layers=model.layout.layers, tp_size=1, tp_rank=0,
            num_heads=model.layout.heads, head_size=model.layout.head_size, device=torch.device('cuda:0'), dtype=torch.float32)

        def set_state(nonzero):
            with torch.no_grad():
                for name, parameter in params.items():
                    parameter.copy_(portable[name] if nonzero else torch.zeros_like(parameter))

        def token_ids(length):
            # Fixed numerical token pattern, independent of task text or role outputs.
            values = (torch.arange(length, dtype=torch.long) * 37 + 101) % model.layout.vocab
            values[0] = tokenizer.bos_token_id
            return values.tolist()

        def serving_state(nonzero):
            recurrent = serving.zero_state(1)
            if nonzero:
                recurrent[1].copy_(profiles.resolve('mechanism').wkv_state.unsqueeze(1))
            return recurrent

        def state_difference(carried, recurrent):
            worst = 0.0
            for i, (wkv, att_shift, ffn_shift) in enumerate(carried):
                for actual, reference in ((wkv[0], recurrent[1][i, 0]), (att_shift[0], recurrent[0][i, 0, 0]),
                                          (ffn_shift[0], recurrent[0][i, 1, 0])):
                    core.require(actual.shape == reference.shape and actual.dtype == reference.dtype,
                                 'carried State layout differs from serving')
                    worst = max(worst, float((actual.float() - reference.float()).abs().max()))
            return worst

        failures = []
        for row in registration['alignment_plans']:
            ids = token_ids(row['tokens'] + 1)
            chunks = episode_chunks(ids, target_spans(row), row['chunk_starts'],
                                    context_tokens=registration['context_tokens'])
            for nonzero in (False, True):
                set_state(nonzero)
                errors, state_errors = [], []
                with torch.inference_mode():
                    recurrent = serving_state(nonzero)
                    carried = None
                    for chunk in chunks:
                        tokens = chunk['input_ids'].cuda()
                        reference = serving.forward_all_logits(tokens, recurrent)
                        actual, carried = model(tokens, carried, return_state=True)
                        errors.append(core.max_logit_difference(actual, reference))
                        state_errors.append(state_difference(carried, recurrent))
                        del actual, reference
                    passed = max(errors) <= registration['max_logit_error'] and max(state_errors) == 0
                    record('chunked_serving_alignment', state='nonzero' if nonzero else 'zero', tokens=row['tokens'],
                           chunk_sizes=chunk_sizes(row), chunk_max_logit_errors=errors,
                           chunk_max_state_errors=state_errors, comparison_passed=passed)
                    failures += [] if passed else [f"alignment {row['tokens']} {'nonzero' if nonzero else 'zero'}"]
                    del recurrent, carried
        del serving
        gc.collect()
        torch.cuda.empty_cache()
        set_state(True)
        frozen = {name: parameter._version for name, parameter in model.named_parameters() if name not in params}
        initial = {name: p.detach().clone() for name, p in params.items()}

        def check_untouched():
            core.require(all(not p.requires_grad and p.grad is None and p._version == frozen[name]
                             for name, p in model.named_parameters() if name in frozen),
                         'frozen base was trained or mutated')
            core.require(all(torch.equal(p.detach(), initial[name]) for name, p in params.items()),
                         'forward/backward mutated initial State')

        for row in registration['gradient_plans']:
            ids = token_ids(row['tokens'] + 1)
            spans = target_spans(row)
            full, = episode_chunks(ids, spans, [0], context_tokens=registration['context_tokens'])
            chunks = episode_chunks(ids, spans, row['chunk_starts'], context_tokens=registration['context_tokens'])
            model.zero_grad(set_to_none=True)
            torch.cuda.reset_peak_memory_stats()
            logits = model(full['input_ids'].cuda())
            loss = core.target_cross_entropy(logits, full['labels'].cuda())
            del logits
            loss.backward()
            full_peak = torch.cuda.max_memory_allocated()
            reference = {name: p.grad.detach().clone() for name, p in params.items()}
            full_loss = float(loss.detach())
            del loss
            model.zero_grad(set_to_none=True)
            torch.cuda.reset_peak_memory_stats()
            result = state_carry_backward(model, chunks, weight=1.0)
            chunked_peak = torch.cuda.max_memory_allocated()
            check_untouched()
            core.require(all(p.grad is not None and bool(torch.isfinite(p.grad).all()) and bool(torch.count_nonzero(p.grad))
                             for p in params.values()), 'chunked State gradient is absent or invalid')
            layer_errors = [float((params[n].grad - reference[n]).norm() / reference[n].norm()) for n in names]
            total_error = float(torch.stack([(params[n].grad - reference[n]).square().sum() for n in names]).sum().sqrt()
                                / torch.stack([reference[n].square().sum() for n in names]).sum().sqrt())
            loss_error = abs(result['loss'] - full_loss) / full_loss
            passed = (result['recompute_equal'] and total_error <= registration['max_gradient_relative_error']
                      and loss_error <= registration['max_loss_relative_error']
                      and result['targets'] == int(full['labels'].ne(-100).sum()))
            record('chunked_gradient', tokens=row['tokens'], chunk_sizes=chunk_sizes(row), targets=result['targets'],
                   full_loss=full_loss, chunked_loss=result['loss'], loss_relative_error=loss_error,
                   gradient_relative_error=total_error, max_layer_gradient_relative_error=max(layer_errors),
                   layer_gradient_relative_errors=layer_errors, recompute_equal=result['recompute_equal'],
                   full_peak_allocated_bytes=full_peak, chunked_peak_allocated_bytes=chunked_peak,
                   base_unchanged=True, state_unchanged=True, comparison_passed=passed)
            failures += [] if passed else [f"gradient {row['tokens']}"]
            core.require(max(full_peak, chunked_peak) <= registration['max_allocated_bytes'],
                         'registered GPU memory budget exceeded')
            del reference
            model.zero_grad(set_to_none=True)

        for row in registration['long_backward_plans']:
            ids = token_ids(row['tokens'] + 1)
            chunks = episode_chunks(ids, target_spans(row), row['chunk_starts'],
                                    context_tokens=registration['context_tokens'])
            model.zero_grad(set_to_none=True)
            torch.cuda.reset_peak_memory_stats()
            begun = time.monotonic()
            result = state_carry_backward(model, chunks, weight=1.0)
            seconds = time.monotonic() - begun
            peak = torch.cuda.max_memory_allocated()
            check_untouched()
            gradients = {name: {'finite': p.grad is not None and bool(torch.isfinite(p.grad).all()),
                                'nonzero': p.grad is not None and bool(torch.count_nonzero(p.grad))}
                         for name, p in params.items()}
            passed = (result['recompute_equal'] and result['chunks'] == len(chunks)
                      and all(v['finite'] and v['nonzero'] for v in gradients.values())
                      and peak <= registration['max_allocated_bytes'])
            record('long_chunked_backward', tokens=row['tokens'], chunk_sizes=chunk_sizes(row), targets=result['targets'],
                   loss=result['loss'], recompute_equal=result['recompute_equal'], seconds=seconds,
                   all_layer_gradients_finite_nonzero=all(v['finite'] and v['nonzero'] for v in gradients.values()),
                   peak_allocated_bytes=peak, base_unchanged=True, state_unchanged=True, comparison_passed=passed)
            failures += [] if passed else [f"long backward {row['tokens']}"]
            model.zero_grad(set_to_none=True)
        if 'episode_dataset' in registration:
            from rwkv_lh.statetune_episodes import load_split
            reference = registration['episode_dataset']
            _, episodes = load_split(reference['path'], reference['sha256'], 'TRAIN.jsonl',
                context_tokens=registration['context_tokens'], vocab_size=int(tokenizer.vocab_size),
                bos_token_id=int(tokenizer.bos_token_id), model_sha256=registration['base_sha256'],
                tokenizer_sha256=manifest['output']['vocab_sha256'])
            requested = registration['episode_probe_ids']
            core.require(bool(requested) and len(set(requested)) == len(requested), 'episode probe identities differ')
            by_id = {row['episode_id']: row for row in episodes}
            core.require(set(requested) <= set(by_id), 'unknown episode probe')
            for episode_id in requested:
                row = by_id[episode_id]
                chunks = episode_chunks(row['token_ids'], row['target_spans'], row['chunk_starts'],
                    context_tokens=registration['context_tokens'], supervised=row['supervised'])
                model.zero_grad(set_to_none=True)
                torch.cuda.reset_peak_memory_stats()
                begun = time.monotonic()
                result = state_carry_backward(model, chunks, weight=1.0)
                torch.cuda.synchronize()
                peak = torch.cuda.max_memory_allocated()
                check_untouched()
                valid_gradient = all(p.grad is not None and bool(torch.isfinite(p.grad).all())
                                     and bool(torch.count_nonzero(p.grad)) for p in params.values())
                passed = result['recompute_equal'] and valid_gradient and peak <= registration['max_allocated_bytes']
                report['role_samples'] += 1
                record('real_episode_backward', episode_id=episode_id, dataset_sha256=reference['sha256'],
                       tokens=len(row['token_ids']), chunks=result['chunks'], targets=result['targets'],
                       loss=result['loss'], recompute_equal=result['recompute_equal'],
                       all_layer_gradients_finite_nonzero=valid_gradient, peak_allocated_bytes=peak,
                       base_unchanged=True, state_unchanged=True, optimizer_steps=0,
                       seconds=time.monotonic() - begun, comparison_passed=passed)
                failures += [] if passed else [f'real episode {episode_id}']
            model.zero_grad(set_to_none=True)
        # Every comparison is recorded before failing, so one mismatch cannot hide the other evidence.
        core.require(not failures, 'State-carry comparisons failed: ' + ', '.join(failures))
        verify_loaded_libraries(runtime)
        record('complete', binary_inventory_verified=True)
    except Exception as exc:
        report['passed'] = False
        report['error'] = {'type': type(exc).__name__, 'message': str(exc)}
        report['elapsed_seconds'] = time.monotonic() - started
        (args.output / 'RESULT.json').write_text(json.dumps(report, indent=2) + '\n')
        raise
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
