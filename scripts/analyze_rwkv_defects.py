"""Evidence-bound boundary inventory; observations are not automatic error labels."""
import argparse
from collections import Counter
import json
from pathlib import Path

from rwkv_lh import model_io
from rwkv_lh.direct_trace_data import replay_run, executed_arguments
from rwkv_lh.harness import HarnessError
from rwkv_lh.offline_teacher_api import write_json, digest


def analyze(root, model_sha256):
    root = Path(root).resolve(strict=True)
    result = json.loads((root / 'RESULT.json').read_text())
    state = json.loads((root / 'state_snapshot.json').read_text())
    previous = (json.loads((root / 'PARENT_STATE_SNAPSHOT.json').read_text())
                if (root / 'PARENT_STATE_SNAPSHOT.json').exists() else {})
    parent_actions = previous.get('actions', {})
    parent_events = previous.get('model_events', {})
    actions = [a for k, a in state['actions'].items() if k not in parent_actions]
    rejections = [e for k, e in state['model_events'].items()
                  if k not in parent_events and e['event_type'] == 'protocol_rejection']
    seen, rows = {}, []
    for cp, boundary in replay_run(root, model_sha256).items():
        raw = boundary['raw_generation']['raw_output']
        row = {'checkpoint_id': cp, 'input_checkpoint_id': boundary['input_checkpoint_id'],
               'request_id': boundary['request_id'], 'input_sha256': digest(boundary['input_text']),
               'raw_output_sha256': digest(raw), 'input_tokens': len(boundary['input_token_ids']),
               'observations': [], 'raw_output': raw}
        try:
            call = model_io.parse_model_command(raw)
            arguments = executed_arguments(call) if call.name != 'final_answer' else call.arguments
            row.update(function=call.name, arguments=arguments)
            key = json.dumps([call.name, arguments], sort_keys=True)
            if key in seen and call.name in ('read_file', 'list_directory', 'search_text'):
                row['observations'].append('repeated_observation_request')
                row['earlier_same_request_checkpoint'] = seen[key]
            seen[key] = cp
        except (ValueError, HarnessError) as exc:
            row['observations'].append('invalid_tool_call')
            row['error'] = str(exc)
        rows.append(row)
    return {'run_root': str(root), 'result_sha256': digest((root / 'RESULT.json').read_text()),
            'agent': {'completed': int(result['termination'] == 'submitted'),
                      'termination_reason': result.get('termination_reason'),
                      'new_tool_actions': len(actions), 'new_protocol_rejections': len(rejections),
                      'model_generations': len(rows)},
            'rejections': rejections, 'boundaries': rows,
            'observations': dict(Counter(o for row in rows for o in row['observations'])),
            'interpretation': 'Repeated requests are candidates for review, not automatically useless. '
                              'Check intervening edits, cursor, prior failures and returned evidence. '
                              'No project success, causality, or training admission is inferred.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-root', type=Path, required=True)
    parser.add_argument('--model-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('analysis output already exists')
    write_json(args.output, analyze(args.run_root, args.model_sha256))


if __name__ == '__main__':
    main()
