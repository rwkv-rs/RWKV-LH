import json
from pathlib import Path
c=json.loads(Path('configs/capacity.json').read_text()); r=json.loads(Path('configs/runtime.json').read_text())
assert c['workers']*10+c['memory']<=120
assert r['mode']=='safe' or (c['workers']>=8 and r['timeout']>=20)
assert c['workers']==8
print('invariants verified')
