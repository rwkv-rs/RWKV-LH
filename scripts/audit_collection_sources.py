"""Stream SFT-Agent JSONL into a structural inventory, never training labels."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rwkv_lh.ultradata import audit_trajectory, _json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    digest = hashlib.sha256()
    count = 0
    with args.source.open('rb') as source, args.output.open('x') as output:
        offset = 0
        for number, raw in enumerate(source, 1):
            digest.update(raw)
            record = {'line': number, 'offset': offset, 'bytes': len(raw),
                      'sha256': hashlib.sha256(raw).hexdigest(), 'revision': args.revision}
            offset += len(raw)
            try:
                row = _json(raw)
                if not isinstance(row, dict):
                    raise ValueError('source row must be an object')
                record['audit'] = audit_trajectory(row)
                record['admission'] = 'requires_environment_reconstruction'
            except (ValueError, UnicodeError) as exc:
                record.update(admission='invalid_source', error=str(exc))
            output.write(json.dumps(record, ensure_ascii=False) + '\n')
            count += 1
    print(json.dumps({'rows': count, 'source_sha256': digest.hexdigest(),
                      'executed_tasks': 0, 'training_rows': 0}))


if __name__ == '__main__':
    main()
