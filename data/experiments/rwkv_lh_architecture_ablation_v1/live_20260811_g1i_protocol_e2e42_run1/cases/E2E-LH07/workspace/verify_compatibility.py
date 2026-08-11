import json
from pathlib import Path
files = sorted(Path('services').glob('service-*.json'))
assert len(files) == 8
values = [json.loads(path.read_text()) for path in files]
assert all(item['schema_version'] == 3 for item in values)
assert all(item['runtime']['channel'] == 'stable' for item in values)
assert all(item['compat']['api'] == 'v3' for item in values)
assert len({item['name'] for item in values}) == 8
print('cross-service compatibility verified')
