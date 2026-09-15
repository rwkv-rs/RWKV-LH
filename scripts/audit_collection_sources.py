"""Stream SFT-Agent JSONL with resumable checkpoints; never training labels."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rwkv_lh.ultradata import audit_trajectory, _json


def audit_source(source_path, revision, output_path, *, resume=False):
    if not re.fullmatch('[0-9a-f]{40}', revision):
        raise ValueError('immutable dataset revision required')
    partial = Path(str(output_path) + '.partial')
    checkpoint = Path(str(output_path) + '.checkpoint.json')
    if output_path.exists():
        raise FileExistsError(output_path)
    identity = {'source': str(source_path.resolve()), 'revision': revision}
    state = {'count': 0, 'offset': 0, 'output_bytes': 0, 'invalid_rows': 0,
             'prefix_sha256': hashlib.sha256().hexdigest(),
             'output_sha256': hashlib.sha256().hexdigest(), **identity}
    if resume:
        state = json.loads(checkpoint.read_text())
        if any(state[key] != value for key, value in identity.items()):
            raise ValueError('audit source identity changed')
    elif checkpoint.exists() or partial.exists():
        raise FileExistsError('partial audit exists; use --resume')
    digest = hashlib.sha256()
    with source_path.open('rb') as source, partial.open('r+b' if resume else 'x+b') as output:
        remaining = state['offset']
        while remaining:
            chunk = source.read(min(1024 * 1024, remaining))
            if not chunk:
                raise ValueError('source prefix shortened')
            digest.update(chunk);remaining -= len(chunk)
        if digest.hexdigest() != state['prefix_sha256']:
            raise ValueError('source prefix changed')
        if output.seek(0, 2) < state['output_bytes']:
            raise ValueError('partial audit shortened')
        output.seek(0)
        output_digest = hashlib.sha256()
        remaining_output = state['output_bytes']
        while remaining_output:
            chunk = output.read(min(1024*1024, remaining_output))
            if not chunk:
                raise ValueError('partial audit shortened')
            output_digest.update(chunk);remaining_output -= len(chunk)
        if output_digest.hexdigest() != state['output_sha256']:
            raise ValueError('partial audit digest changed')
        output.truncate(state['output_bytes']);output.seek(state['output_bytes'])
        def commit():
            output.flush();os.fsync(output.fileno())
            state.update(output_bytes=output.tell(), prefix_sha256=digest.hexdigest(),
                         output_sha256=output_digest.hexdigest())
            temporary = Path(str(checkpoint) + '.tmp')
            with temporary.open('w') as stream:
                json.dump(state, stream);stream.flush();os.fsync(stream.fileno())
            os.replace(temporary, checkpoint)
        commit()
        for raw in source:
            record = {'line': state['count'] + 1, 'offset': state['offset'], 'bytes': len(raw),
                      'sha256': hashlib.sha256(raw).hexdigest(), 'revision': revision}
            digest.update(raw)
            state['offset'] += len(raw);state['count'] += 1
            try:
                row = _json(raw)
                if not isinstance(row, dict):
                    raise ValueError('source row must be an object')
                record['audit'] = audit_trajectory(row)
                record['admission'] = 'requires_environment_reconstruction'
            except (ValueError, UnicodeError, TypeError, RecursionError) as exc:
                record.update(admission='invalid_source', error=f'{type(exc).__name__}: {exc}')
                state['invalid_rows'] += 1
            encoded = (json.dumps(record, ensure_ascii=False) + '\n').encode()
            output.write(encoded);output_digest.update(encoded)
            if state['count'] % 100 == 0:
                commit()
        commit()
    os.replace(partial, output_path)
    return {'rows': state['count'], 'invalid_rows': state['invalid_rows'],
            'source_sha256': digest.hexdigest(), 'executed_tasks': 0, 'training_rows': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    print(json.dumps(audit_source(args.source, args.revision, args.output, resume=args.resume)))


if __name__ == '__main__':
    main()
