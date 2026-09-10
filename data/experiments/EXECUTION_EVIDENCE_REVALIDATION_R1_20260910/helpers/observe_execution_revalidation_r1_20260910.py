"""Read compact live progress from SQLite without editing the Agent workspace."""
from pathlib import Path
from collections import Counter
import json
import sqlite3
import sys

ROOT = Path('/home/chase/GitHub/RWKV-LH')
sys.path.insert(0, str(ROOT))
from rwkv_lh.store import LongHorizonStore

rows = []
for name in ('ULTRADATA_EXECUTION_REVALIDATION_R1_20260910', 'REALPROJECT_EXECUTION_REVALIDATION_R1_20260910'):
    folder = ROOT / 'data/experiments' / name
    for case in json.loads((folder / 'REGISTRATION.json').read_text())['task_ids']:
        if (folder / f'{case}.completion.json').exists():
            continue
        path = folder / 'all_zero/cases' / case / 'state/long_horizon.db'
        if not path.exists():
            continue
        with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=3) as connection:
            record = connection.execute('SELECT state_json FROM runs WHERE run_id=?', (case,)).fetchone()
        if record is None:
            continue
        state = LongHorizonStore._deserialize(record[0])
        events = state.get('causal_records', {})
        if isinstance(events, dict):
            events = list(events.values())
        counts = Counter(e['event_type'] for e in events)
        rows.append({'task_id': case, 'revision': state.get('revision'),
                     'actions_finished': counts['action_finished'],
                     'plans_committed': counts['goal_plan_patch_committed'],
                     'protocol_rejections': counts['protocol_rejection_recorded'],
                     'last_events': [{'event_type': e['event_type'], 'event_id': e.get('event_id')} for e in events[-4:]]})
print(json.dumps(rows, ensure_ascii=False))
