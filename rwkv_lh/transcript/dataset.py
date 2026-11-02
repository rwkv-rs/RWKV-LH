"""Seal a transcript-token dataset version from an admitted, externally verified export.

Admission (sealed source identity, external acceptance, defect gates) is decided
upstream by the data engine's export (same layout as the former collector's
``train-export``; sources must be single-agent conversations, see
``frozen.training_messages``); this module takes its byte copies
and acceptance evidence and performs the single source -> token conversion with
the current codec, exactly as ``frozen.load_split`` recomputes it. Rows the
current protocol cannot represent are excluded with a reason, never repaired or
truncated. Validation is held out by scenario family so near-duplicate tasks of
one scenario never straddle the split.

    python -m rwkv_lh.transcript.dataset PRODUCTION_ROOT OUTPUT ADMITTED_EXPORT [ADMITTED_EXPORT ...] \
        --model-sha256 SHA --context-tokens N --owner-instruction FILE
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile

from . import frozen
from ..project_protocols.agent import is_host_notice
from ..evaluation_policy import assert_training_record_allowed, assert_training_source_allowed
from .parse import STORAGE_PROTOCOL, loads, parse_transcript, validate_messages
from .render import compact
from .tokenize import tokenize_transcript
from .tools import TOOL_PROTOCOL, canonical_definitions
from .wire import PROTOCOL

VALIDATION_MODULUS = 16  # about 6% of scenario families


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _ref(path, base):
    return {'path': path.relative_to(base).as_posix(), 'sha256': _sha(path.read_bytes())}


def validation_family(family):
    return int(_sha(family.encode('utf-8')), 16) % VALIDATION_MODULUS == 0


def _shingles(text, n=5):
    text = re.sub(r'\s+', ' ', text)
    return {text[i:i + n] for i in range(max(1, len(text) - n + 1))}


def similarity_audit(prompts):
    """Highest character 5-gram Jaccard from each validation prompt to any train prompt."""
    train = [(key, _shingles(text)) for key, (split, text) in prompts.items() if split == 'train']
    worst = []
    for key, (split, text) in prompts.items():
        if split != 'validation':
            continue
        mine = _shingles(text)
        score, nearest = max(((len(mine & other) / len(mine | other), name) for name, other in train),
                             default=(0.0, None))
        worst.append({'episode_id': key, 'max_jaccard': round(score, 4), 'nearest_train': nearest})
    worst.sort(key=lambda item: -item['max_jaccard'])
    return {'method': 'character 5-gram Jaccard over the original task prompt; families held out whole',
            'validation_episodes': len(worst), 'max': worst[0]['max_jaccard'] if worst else 0.0,
            'top': worst[:20]}


def build_dataset(admitted, production_root, output, *, model_sha256, context_tokens, owner_instruction,
                  native_tools, tokenizer, tokenizer_sha256):
    # One export directory, or the shard directories of the collector's bulk export.
    shards = [Path(admitted)] if isinstance(admitted, (str, Path)) else [Path(item) for item in admitted]
    production_root, output = Path(production_root), Path(output).absolute()
    if not shards:
        raise ValueError('at least one admitted export is required')
    if output.exists():
        raise FileExistsError('dataset versions are immutable; choose a new output directory')
    if not isinstance(owner_instruction, str) or not owner_instruction.strip():
        raise ValueError('the owner instruction authorizing this dataset is required')
    assert_training_source_allowed(production_root)
    sources, upstream_rows = {}, []
    for shard in shards:
        assert_training_source_allowed(shard)
        upstream = loads((shard / 'sources.json').read_bytes())
        assert_training_record_allowed(upstream)
        if upstream.get('origin') != 'production':
            raise ValueError('admitted export must come from production sources')
        for entry in upstream['files']:
            assert_training_record_allowed(entry)
            source = shard / entry['path']
            assert_training_source_allowed(source)
            sources[entry['sha256']] = source
        upstream_rows += (shard / 'train.jsonl').read_text(encoding='utf-8').splitlines()
    catalog = canonical_definitions(native_tools)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.dataset-', dir=output.parent) as staging:
        stage = Path(staging) / 'dataset'
        (stage / 'sources').mkdir(parents=True)
        rows, files, excluded = {'train': [], 'validation': []}, [], Counter()
        excluded_runs, prompts, coverage = {}, {}, {'train': Counter(), 'validation': Counter()}
        lengths, seen = {'train': [], 'validation': []}, set()
        for line in upstream_rows:
            upstream_row = loads(line)
            assert_training_record_allowed(upstream_row)
            episode, digest = upstream_row['episode_id'], upstream_row['source']
            def skip(reason):
                excluded[reason] += 1
                excluded_runs[episode] = reason
            raw = sources[digest].read_bytes()
            if _sha(raw) != digest:
                raise ValueError('admitted source bytes differ from their identity: ' + episode)
            assert_training_source_allowed(production_root / episode)
            freeze = loads((production_root / episode / 'freeze.json').read_bytes())
            assert_training_record_allowed(freeze)
            assert_training_record_allowed(freeze['task'])
            sealed = loads((production_root / episode / 'manifest.json').read_bytes())
            if sealed.get('native_messages.json') != digest:
                raise ValueError('admitted source is not the sealed production transcript: ' + episode)
            if digest in seen or episode in seen:
                raise ValueError('duplicate episode or production source in admitted export: ' + episode)
            seen.update((digest, episode))
            acceptance = frozen.validate_row_acceptance(upstream_row['acceptance'], episode_id=episode)
            document = parse_transcript(raw)
            try:
                validate_messages(document['messages'], allow_pending=False)
                if document['tools'] != catalog:
                    raise ValueError('catalog differs')
                messages = frozen.training_messages(document['messages'], native_tools)
                encoded = tokenize_transcript(messages, tokenizer=tokenizer, native_tools=native_tools,
                                              max_tokens=context_tokens)
            except ValueError as exc:
                text = str(exc)
                skip('over_context' if 'capacity' in text else 'delimiter_in_text' if 'delimiter' in text
                     else 'text_only_turn' if 'at least one tool call' in text else 'protocol_rejected')
                continue
            split = 'validation' if validation_family(freeze['task']['family']) else 'train'
            target = stage / 'sources' / (episode + '.json')
            target.write_bytes(raw)
            files.append({'path': 'sources/' + target.name, 'sha256': digest, 'input_protocol': STORAGE_PROTOCOL})
            row = frozen.validate_token_row({'episode_id': episode, 'source': digest, 'input_protocol': PROTOCOL,
                'input_ids': encoded['input_ids'], 'loss_mask': encoded['loss_mask'], 'acceptance': acceptance},
                context_tokens=context_tokens)
            rows[split].append(row)
            prompts[episode] = (split, freeze['task']['prompt'])
            coverage[split]['family:' + freeze['task'].get('defect_family', 'unknown')] += 1
            names = {call['function']['name'] for m in document['messages'] for call in m.get('tool_calls', [])}
            coverage[split].update('tool:' + name for name in names)
            requests = sum(m['role'] == 'user' and not is_host_notice(m) for m in messages)
            coverage[split]['user_requests:' + str(requests)] += 1
            lengths[split].append((len(row['input_ids']), sum(row['loss_mask'])))
        if not rows['train'] or not rows['validation']:
            raise ValueError('both train and validation splits must be nonempty')
        source_manifest = stage / 'sources.json'
        source_manifest.write_text(json.dumps({'schema_version': frozen.SOURCE_SCHEMA, 'origin': 'production',
                                               'files': files}, ensure_ascii=False, indent=2) + '\n')
        splits = {}
        for split, items in rows.items():
            path = stage / (split + '.jsonl')
            path.write_text(''.join(compact(row) + '\n' for row in items), encoding='utf-8')
            splits[split] = {**_ref(path, stage), 'rows': len(items)}
        script = stage / 'generation_script.py'
        shutil.copyfile(__file__, script)
        protocol_dir = Path(frozen.__file__).parent
        manifest = {'schema_version': frozen.MANIFEST_SCHEMA, 'input_protocol': PROTOCOL,
            'tool_protocol': TOOL_PROTOCOL, 'model_sha256': model_sha256, 'tokenizer_sha256': tokenizer_sha256,
            'protocol_sources': {name: _sha((protocol_dir / name).read_bytes()) for name in frozen.PROTOCOL_FILES},
            'generation_script': _ref(script, stage), 'source_manifest': _ref(source_manifest, stage),
            'splits': splits}
        manifest['data_digest'] = frozen.data_digest(manifest)
        binding = {'data_digest': manifest['data_digest'],
                   'source_manifest_sha256': manifest['source_manifest']['sha256'],
                   'owner_instruction': owner_instruction}
        def stats(items):
            tokens = sorted(t for t, _ in items)
            return {'episodes': len(items), 'input_tokens': sum(tokens), 'supervised_tokens': sum(s for _, s in items),
                    'p50': tokens[len(tokens) // 2], 'p90': tokens[int(len(tokens) * .9)], 'max': tokens[-1]}
        audits = {
            'split': {'rule': 'validation iff sha256(task.family) mod %d == 0' % VALIDATION_MODULUS,
                      'train': stats(lengths['train']), 'validation': stats(lengths['validation'])},
            'similarity': similarity_audit(prompts),
            'coverage': {split: dict(sorted(counter.items())) for split, counter in coverage.items()},
        }
        (stage / 'authorization.json').write_text(json.dumps(binding, ensure_ascii=False, indent=2) + '\n')
        (stage / 'audit.json').write_text(json.dumps({**binding, 'training_eligible': True, 'audits': audits},
                                                     ensure_ascii=False, indent=2) + '\n')
        manifest['authorization_references'] = [_ref(stage / 'authorization.json', stage)]
        manifest['audit_references'] = [_ref(stage / 'audit.json', stage)]
        (stage / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
        report = {'output': str(output), 'manifest_sha256': _sha((stage / 'manifest.json').read_bytes()),
                  'admitted': [str(shard) for shard in shards],
                  'rows': {split: len(items) for split, items in rows.items()},
                  'excluded': dict(excluded), 'excluded_runs': excluded_runs, 'audits': audits}
        (stage / 'BUILD_REPORT.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        stage.rename(output)
    return report


def main(argv=None):
    from ..harness import ActionHarness
    from ..project_runtime import agent_definitions
    from ..token_budget import VOCAB_PATH, tokenizer
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('production_root', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('admitted', type=Path, nargs='+', help='export directory or bulk-export shard directories')
    parser.add_argument('--model-sha256', required=True)
    parser.add_argument('--context-tokens', type=int, required=True)
    parser.add_argument('--owner-instruction', type=Path, required=True)
    args = parser.parse_args(argv)
    report = build_dataset(args.admitted, args.production_root, args.output,
        model_sha256=args.model_sha256, context_tokens=args.context_tokens,
        owner_instruction=args.owner_instruction.read_text(encoding='utf-8'),
        native_tools=agent_definitions(ActionHarness()), tokenizer=tokenizer(),
        tokenizer_sha256=_sha(VOCAB_PATH.read_bytes()))
    print(json.dumps({key: report[key] for key in ('output', 'manifest_sha256', 'rows', 'excluded')},
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
