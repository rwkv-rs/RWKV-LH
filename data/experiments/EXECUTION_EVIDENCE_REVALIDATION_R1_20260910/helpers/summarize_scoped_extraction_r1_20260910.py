"""Report source admission separately from unchanged role-data quality gates."""
from pathlib import Path
import hashlib
import json

ROOT = Path('/home/chase/GitHub/RWKV-LH')
OUT = ROOT / 'data/experiments/EXECUTION_EVIDENCE_REVALIDATION_R1_20260910'
path = OUT / 'scoped_selector_candidates/manifest.json'
value = json.loads(path.read_text())
summary = {
    'agent_metrics': 'No additional Agent result from extraction; 15-task rerun separate.',
    'requested_sources': 14, 'excluded_source': 'RP-WEB-02',
    'original_15_source_waiver': 'draft; no unanimous acceptance',
    'status': value['status'], 'counts_by_role': value['counts_by_role'],
    'review_queue_rows': len((OUT / 'scoped_selector_candidates/review_queue.jsonl').read_text().splitlines()),
    'coverage_audit': value['coverage_audit'], 'quality_gates': value['quality_gates'],
    'provenance_keys': sorted(value['provenance']),
    'similarity_keys': sorted(value.get('similarity_audit', {})),
    'manifest_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
    'optimizer_steps': 0,
}
for key, item in value['provenance'].items():
    if key in ('source_runs', 'sources', 'source_errors', 'errors'):
        summary[key] = item
audit = value.get('similarity_audit', {})
summary['similarity_summary'] = {k: (len(v) if isinstance(v, list) else v) for k, v in audit.items()}
with (OUT / 'SCOPED_EXTRACTION_SUMMARY.json').open('x') as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)
    f.write('\n')
print(json.dumps({k: v for k, v in summary.items() if k != 'source_runs'}, ensure_ascii=False))
