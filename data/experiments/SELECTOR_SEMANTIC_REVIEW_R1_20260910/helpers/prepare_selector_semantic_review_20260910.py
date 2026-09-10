"""Present all 126 existing rows grouped by real boundary, without supplying labels."""
from collections import defaultdict
from pathlib import Path
import hashlib
import json
ROOT = Path('/home/chase/GitHub/RWKV-LH')
OUT = ROOT / 'data/experiments/SELECTOR_SEMANTIC_REVIEW_R1_20260910'
SOURCE = ROOT / 'data/experiments/EXECUTION_EVIDENCE_REVALIDATION_R1_20260910/scoped_selector_candidates/review_queue.jsonl'
OUT.mkdir(exist_ok=False)
rows = [json.loads(line) for line in SOURCE.read_text().splitlines()]
groups = defaultdict(list)
for row in rows:
    groups[(row['source_run_id'], row['run_id'], row['boundary_event_id'])].append(row)
index = []
for number, (identity, group) in enumerate(sorted(groups.items()), 1):
    canonical = {json.dumps(row['protocol_source'], sort_keys=True) for row in group}
    if len(canonical) != 1:
        raise SystemExit('Boundary sources differ: ' + str(identity))
    packet = {'packet_id': f'B{number:03d}', 'source_run_id': identity[0], 'run_id': identity[1],
              'boundary_event_id': identity[2], 'protocol_source': group[0]['protocol_source'],
              'rows': [{key: row.get(key) for key in ('sample_id', 'request_id', 'original_target_text',
                                                    'original_output_record_sha256', 'available_evidence_refs', 'split')}
                       | {'input_sha256': hashlib.sha256(row['input_text'].encode()).hexdigest()}
                       for row in group]}
    file = OUT / (packet['packet_id'] + '.json')
    file.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + '\n')
    index.append({'packet_id': packet['packet_id'], 'run_id': identity[1], 'boundary': identity[2],
                  'rows': len(group), 'path': str(file), 'sha256': hashlib.sha256(file.read_bytes()).hexdigest(),
                  'subtask': group[0]['protocol_source']['current_subtask']})
manifest = {'source_path': str(SOURCE), 'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            'row_count': len(rows), 'boundary_count': len(groups), 'packets': index,
            'authorization': 'Owner 2026-09-10 explicitly enables two independent AI semantic reviewers for all126 rows',
            'rule': 'Review all rows. Accept original only with source-visible justification; otherwise explicit eligible correction with rationale or reject as ambiguous/unsupported. No fabricated evidence, protocol fields, or training approvals.',
            'independence': 'Reviewers do not read each other decisions before submission. Disagreement remains excluded; never auto-accept.',
            'optimizer_steps': 0}
(OUT / 'MANIFEST.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'rows': len(rows), 'boundaries': len(groups), 'protocol_source_keys': list(rows[0]['protocol_source']),
                  'manifest_sha256': hashlib.sha256((OUT / 'MANIFEST.json').read_bytes()).hexdigest()}))
