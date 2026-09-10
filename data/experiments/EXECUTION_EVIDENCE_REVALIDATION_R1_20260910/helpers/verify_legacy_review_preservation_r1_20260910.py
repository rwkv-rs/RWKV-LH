"""Prove the nine existing review packets still bind the re-extracted raw rows."""
from pathlib import Path
import hashlib
import json

ROOT = Path('/home/chase/GitHub/RWKV-LH')
OUT = ROOT / 'data/experiments/EXECUTION_EVIDENCE_REVALIDATION_R1_20260910'
PACKET = ROOT / 'data/experiments/SELECTOR_REVIEW_PACKET_R1_20260910'
manifest = json.loads((PACKET / 'MANIFEST.json').read_text())
old_path = Path(manifest['source'])
if hashlib.sha256(old_path.read_bytes()).hexdigest() != manifest['source_sha256']:
    raise SystemExit('Historical packet source SHA mismatch')
old = {r['sample_id']: r for r in map(json.loads, old_path.read_text().splitlines())}
new_path = OUT / 'scoped_selector_candidates/review_queue.jsonl'
new = {r['sample_id']: r for r in map(json.loads, new_path.read_text().splitlines())}
rows = []
for path in sorted(PACKET.glob('ULTRA-Code_*.json')):
    packet = json.loads(path.read_text())
    for selection in packet['original_selections']:
        before = old[selection['sample_id']]
        after = new[selection['sample_id']]
        checks = {
            'complete_raw_row_equal': before == after,
            'input_sha_equal_packet': hashlib.sha256(after['input_text'].encode()).hexdigest() == selection['input_sha256'],
            'boundary_equal': after['boundary_event_id'] == packet['boundary_event_id'],
            'protocol_source_equal': after['protocol_source'] == packet['protocol_source'],
        }
        for field in ('request_id', 'original_target_text', 'original_output_record_sha256', 'available_evidence_refs'):
            checks[field + '_equal_packet'] = after[field] == selection[field]
        rows.append({'packet_path': str(path), 'packet_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                     'sample_id': selection['sample_id'], 'checks': checks, 'all_equal': all(checks.values())})
value = {'boundaries': len({r['packet_path'] for r in rows}), 'menu_rows': len(rows),
         'all_preserved': len(rows) == 27 and all(r['all_equal'] for r in rows),
         'approved_labels': 0, 'label_review_status_unchanged': True,
         'new_review_queue_sha256': hashlib.sha256(new_path.read_bytes()).hexdigest(), 'rows': rows}
with (OUT / 'LEGACY_REVIEW_PRESERVATION.json').open('x') as f:
    json.dump(value, f, ensure_ascii=False, indent=2)
    f.write('\n')
print(json.dumps({k: v for k, v in value.items() if k != 'rows'}, ensure_ascii=False))
if not value['all_preserved']:
    raise SystemExit(1)
