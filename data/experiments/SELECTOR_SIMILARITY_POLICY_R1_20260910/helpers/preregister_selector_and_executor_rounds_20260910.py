"""Freeze downstream analysis policies before new collection/budget outcomes."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
ROOT = Path('/home/chase/GitHub/RWKV-LH')
old = ROOT / 'data/experiments/EXECUTION_EVIDENCE_REVALIDATION_R1_20260910/scoped_selector_candidates/candidates.jsonl'
rows = [json.loads(line) for line in old.read_text().splitlines()]
anchors = [row for row in rows if row['split'] in ('dev', 'confirmation')]
stamp = datetime.now(timezone.utc).isoformat()
out = ROOT / 'data/experiments/SELECTOR_SIMILARITY_POLICY_R1_20260910'
out.mkdir(exist_ok=False)
policy = {'registered_at': stamp, 'owner_authorization': '2026-09-10 owner explicitly requests preregistered clustering before Selector training',
    'input_anchor_path': str(old), 'input_anchor_sha256': hashlib.sha256(old.read_bytes()).hexdigest(),
    'role': 'selector_intent', 'algorithm': 'UTF8 byte5gram count-vector cosine on unmodified full input_text',
    'threshold': 0.95, 'exact_comparison': 'dot^2*10000 >=9025*left_norm_squared*right_norm_squared',
    'split_policy': 'Keep exact existing project-family hash split; never move rows or rename families.',
    'evaluation_anchor_sample_ids': [row['sample_id'] for row in anchors],
    'evaluation_anchor_policy': 'Preserve all five existing dev/confirmation candidate rows byte-for-byte. No promotion of train rows to validation. These are candidate anchors, not a fabricated valid prior-regression artifact.',
    'clustering_unit': 'Actual selection boundary, including its admitted menu rows; do not fragment three-menu decision evidence.',
    'graph_edges': 'Same-role boundary units connect if any pair of their unmodified input_text rows meets threshold; include same-split edges for transitive leakage control.',
    'component_policy': 'If a component touches any evaluation anchor, remove all train boundary units in it. If a component is train-only, keep one lexicographically smallest (source_run_id,run_id,boundary_event_id) unit and its menu rows; reject other train units.',
    'evaluation_conflict': 'Do not drop or relabel evaluation anchors. Any dev/confirmation cross-split conflict is a failed gate requiring a separately registered next round.',
    'new_rows': 'Only verified production-source samples with already admitted automatic or independent dual-reviewed labels; apply the same fixed rule. New nontrain rows do not replace the five anchors.',
    'rejections': 'Keep a complete exclusion ledger with sample identity, SHA, component, and reason; never relabel exclusions as pending review.',
    'postchecks': ['existing production cross-split similarity audit reports zero violations', 'immutable anchors unchanged', 'required execute/mutate/py_root/missing_target coverage', 'nonempty splits', 'registered sample/boundary minimums'],
    'if_insufficient': 'Report insufficient evidence and collect a separately registered source; never change threshold, input normalization, tie-break, or fixed splits to pass.',
    'optimizer_steps': 0}
(out / 'PREREGISTRATION.json').write_text(json.dumps(policy, ensure_ascii=False, indent=2) + '\n')
budget = ROOT / 'data/experiments/EXECUTOR_OUTPUT_BUDGET_R1_20260910'
budget.mkdir(exist_ok=False)
registration = {'registered_at': stamp, 'owner_authorization': '2026-09-10 owner explicitly requests separate Executor1800->3600 budget experiment',
    'production_commit': '21c0cf45', 'tasks': ['RP-FULL-02', 'RP-WEB-02'],
    'arms_in_order': [{'id': 'baseline1800', 'executor_max_output_tokens': 1800}, {'id': 'candidate3600', 'executor_max_output_tokens': 3600}],
    'schedule': 'Start only after COMMAND_PATH_COLLECTION_R1_20260910 completes. Run both fresh arms; do not reuse historical or command-collection scores as baseline.',
    'runtime_override': 'Identical bounded experiment driver delegates LongHorizonModel.next_command to the unchanged production method with one explicit max_output_tokens argument. No source or prompt patch; persist driver SHA and per-arm config SHA.',
    'fixed': {'all_role_states': 'zero', 'temperature': 0.1, 'max_transitions': 200, 'case_wall_seconds': 1800,
              'case_concurrency': 1, 'native_transport_resume_attempts': 1, 'supervisor_pending_resume_attempts': 0,
              'supervisor': 'unchanged official deepseek-v4-pro low thinking', 'total_wall_seconds': 7200},
    'primary': 'Count every Executor returned generation with finish_reason=length, including retries; separately record Executor generations and length rate.',
    'keep': ['both arms have complete raw results for both tasks, no wall-budget exhaustion or infrastructure failure',
             'baseline length count >0; candidate total length count <=50% of baseline and candidate length rate < baseline',
             'candidate Strict total >=baseline Strict total and no previously passing case becomes failing'],
    'secondary': ['completed', 'mutation count', 'terminal reasons', 'per-case length counts', 'runtime errors', 'elapsed time and token usage'],
    'interpretation': 'Pilot comparison on two affected tasks; a numerical KEEP is not evidence beyond historical Agent noise or final architecture acceptance.',
    'no_adaptive_rerun': True, 'no_rescore': True, 'optimizer_steps': 0}
(budget / 'PREREGISTRATION.json').write_text(json.dumps(registration, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'similarity_policy_sha256': hashlib.sha256((out / 'PREREGISTRATION.json').read_bytes()).hexdigest(),
                  'budget_registration_sha256': hashlib.sha256((budget / 'PREREGISTRATION.json').read_bytes()).hexdigest(),
                  'immutable_evaluation_anchor_rows': len(anchors)}))
