import json
labels = ["maple", "cedar", "pine"]
assert len(labels) == len(set(labels)) == 3
print(json.dumps({"checked": 3, "passed": 3, "scope": "label uniqueness only"}))
