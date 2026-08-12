import json
from pathlib import Path
from pipeline import normalize,validate,total,build
raw=json.loads(Path('orders.json').read_text())
assert normalize(' Beta ')=='beta', 'stage 1 normalize'
items=[{**x,'name':normalize(x['name'])} for x in raw]
assert all(validate(x) for x in items) and not validate({'name':'','quantity':0,'price':-1}), 'stage 2 validate'
assert [total(x) for x in items]==[8,15], 'stage 3 total'
expected={'items':[{'name':'alpha','total':15},{'name':'beta','total':8}],'grand_total':23}
assert build(items)==expected, 'stage 4 build'
assert json.loads(Path('release.json').read_text())==expected, 'stage 5 artifact'
print('pipeline verified')
