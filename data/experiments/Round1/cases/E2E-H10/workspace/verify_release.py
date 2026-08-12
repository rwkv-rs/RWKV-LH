import json
from pathlib import Path

data=json.loads(Path('release/inventory.json').read_text())
assert data['items']==[{'sku':'A1','total':18.0},{'sku':'B2','total':18.0},{'sku':'C3','total':4.5}]
assert data['grand_total']==40.5
report=Path('release/REPORT.md').read_text()
for text in ['A1: 18.0','B2: 18.0','C3: 4.5','Grand total: 40.5']:
    assert text in report
print('release verified')
