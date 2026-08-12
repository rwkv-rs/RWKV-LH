import json
from pathlib import Path
c=json.loads(Path('config.json').read_text())
assert c=={'schema_version':2,'runtime':{'request_timeout_ms':3000,'retries':4,'mode':'safe'},'metadata':{'owner':'ops'}}
r=json.loads(Path('migration_report.json').read_text())
assert r=={'from_version':1,'to_version':2,'renamed':['retry_count->retries','timeout->request_timeout_ms']}
print('config verified')
