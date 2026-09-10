"""Compact public action and generation facts for causal interpretation."""
from pathlib import Path
import json
import sys
ROOT = Path('/home/chase/GitHub/RWKV-LH')
OUT = ROOT / 'data/experiments/EXECUTION_EVIDENCE_REVALIDATION_R2_20260910'
for case in sys.argv[1:]:
    audit = json.loads((OUT / 'all_zero/cases' / case / 'audit.json').read_text())
    actions = [{key: action.get(key) for key in ('action_id', 'action_type', 'arguments', 'status', 'summary', 'tool_output')}
               for action in audit['action_ledger'].values()]
    generations = []
    for event in audit['model_trace']:
        if event.get('type') != 'model_session_generation_returned':
            continue
        raw = event.get('raw_generation', {})
        generations.append({'request_id': event['request_id'], 'role': event.get('model_role'),
                            'finish_reason': event.get('finish_reason'),
                            'max_output_tokens': raw.get('max_output_tokens'),
                            'output_token_count': len(raw.get('raw_token_ids', [])),
                            'output_sha256': raw.get('raw_output_sha256'),
                            'output_prefix': event.get('raw_output', '')[:160],
                            'output_suffix': event.get('raw_output', '')[-160:]})
    result = {'case': case, 'actions': actions, 'generations': generations}
    path = OUT / f'{case}.PUBLIC_ACTION_GENERATION_FACTS.json'
    if not path.exists():
        with path.open('x') as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
    print(json.dumps(result, ensure_ascii=False))
