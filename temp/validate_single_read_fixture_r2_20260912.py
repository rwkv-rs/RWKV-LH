"""Read-only preflight for historical read-result / workspace identity."""
from pathlib import Path
import hashlib

def validate_fixture(case, root):
    workspace=Path(root)/case['workspace_source']
    target=workspace/case['path']
    if case['category']=='missing':
        if target.exists():
            raise ValueError('missing-file fixture contains target')
        if (case['source_result'].get('error') or {}).get('type')!='FileNotFoundError':
            raise ValueError('missing fixture lacks historical FileNotFoundError')
        return
    if not target.is_file():
        raise ValueError('successful-read fixture lacks regular target')
    data=target.read_bytes()
    result=case['source_result']
    artifact=next((a for a in result['artifacts'] if Path(a['path'])==Path(case['path'])),None)
    if not artifact or hashlib.sha256(data).hexdigest()!=artifact['sha256']:
        raise ValueError('successful-read fixture differs from historical artifact')
    metadata=result['metadata']
    if result['output'].encode('utf-8')!=data[metadata['start_byte']:metadata['end_byte']]:
        raise ValueError('historical output differs from fixture bytes')
