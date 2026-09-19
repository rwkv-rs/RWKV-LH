import json
print(json.dumps({"checks": [{"name": "shape", "passed": True}, {"name": "required_key", "passed": False}], "passed": False}))
