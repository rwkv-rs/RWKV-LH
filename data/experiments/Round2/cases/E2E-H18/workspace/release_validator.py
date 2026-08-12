import json
from pathlib import Path
p=json.loads(Path('release/products.json').read_text())
assert p=={'items':[{'sku':'A1','total':27.0},{'sku':'M5','total':6.0},{'sku':'Z9','total':18.0}],'grand_total':51.0}
text=Path('release/REPORT.md').read_text()
for value in ['A1: 27.0','M5: 6.0','Z9: 18.0','Grand total: 51.0']: assert value in text
print('release verified')
