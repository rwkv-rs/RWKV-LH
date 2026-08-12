import json
from pathlib import Path
from project.pipeline import normalize, validate, price, build_release

records = json.loads(Path('orders.json').read_text())
assert normalize(' Alpha ') == 'alpha', 'layer A: normalize must trim and lowercase'
normalized = [{**item, 'name': normalize(item['name'])} for item in records]
invalid = {'name': '', 'qty': 0, 'unit_price': -1}
assert all(validate(item) for item in normalized) and not validate(invalid), 'layer B: records require a nonempty lowercase name and positive integer qty/unit_price'
assert [price(item) for item in normalized] == [6, 5], 'layer C: price must multiply qty by unit_price'
expected = {'items': [{'name': 'alpha', 'total': 6}, {'name': 'beta', 'total': 5}], 'grand_total': 11}
assert build_release(normalized) == expected, 'layer D: build_release has the wrong structure'
artifact = json.loads(Path('release/release.json').read_text())
assert artifact == expected, 'release artifact is missing or inconsistent'
print('release verified')
