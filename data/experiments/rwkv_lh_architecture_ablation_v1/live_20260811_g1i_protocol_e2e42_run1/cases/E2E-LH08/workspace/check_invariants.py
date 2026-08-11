import json
from pathlib import Path
a = json.loads(Path('configs/a.json').read_text())
b = json.loads(Path('configs/b.json').read_text())
c = json.loads(Path('configs/c.json').read_text())
assert a['limit'] + b['reserve'] <= 80, 'capacity invariant violated'
assert c['mode'] == 'safe' or a['limit'] >= 20, 'fast mode requires limit >= 20'
assert b['reserve'] == 70, 'highest-priority change was not retained'
print('invariants verified')
