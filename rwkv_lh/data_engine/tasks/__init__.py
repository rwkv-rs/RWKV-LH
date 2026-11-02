"""Frozen, original project tasks and their content identities."""
import hashlib
import json
from pathlib import Path

def dump(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"

def checksum(value):
    return hashlib.sha256(dump(value).encode()).hexdigest()

def load_task(path):
    task = json.loads(Path(path).read_text())
    if checksum({k:v for k,v in task.items() if k != "digest"}) != task["digest"]:
        raise ValueError("task identity differs")
    return task
