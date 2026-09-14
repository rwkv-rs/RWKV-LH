"""Opt-in offline correction evidence at real generation boundaries.

This audit wrapper does not modify input, output, State or tools. Production
execution does not enable it by default. File copies consume the task deadline.
"""
import hashlib
import json
from pathlib import Path
import re
from .workspace_snapshot import copy_verified_workspace, tree_identity
from .statetune_core import require

SNAPSHOT_SCHEMA = 'rwkv-lh.correction-generation-snapshot.v1'


def _tree_sha(tree):
    return hashlib.sha256(json.dumps(tree,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def generation_snapshot_audit(*, workspace, output, audit_hook):
    """Capture immutable bytes before forwarding generation_started to audit."""
    def audit(event):
        if event.get('type') == 'model_session_generation_started':
            request = event['request_id']
            require(isinstance(request,str) and re.fullmatch(r'[A-Za-z0-9_.-]{1,128}',request)
                    and request not in ('.','..'), 'unsafe generation snapshot request')
            directory=Path(output)/'generation_snapshots'/request
            require(Path(workspace).resolve() not in directory.resolve().parents,
                    'generation evidence overlaps workspace')
            directory.mkdir(parents=True,exist_ok=False)
            tree=copy_verified_workspace(workspace,directory/'before',exclude_git=False,
                                         audit_path=directory/'COPY.json')
            record={'schema_version':SNAPSHOT_SCHEMA,'request_id':request,
                    'input_checkpoint_id':event['input_checkpoint_id'],
                    'input_digest':event['input_digest'],'tree_sha256':_tree_sha(tree)}
            (directory/'SNAPSHOT.json').write_text(json.dumps(record,indent=2)+'\n')
            audit_hook({'type':'correction_generation_snapshot_saved',**record})
        audit_hook(event)
    return audit


def validate_generation_snapshot(root, actual, source_files, *, snapshot=None):
    """Require sealed snapshot immediately before the exact original request."""
    root=Path(root).resolve(strict=True)
    request=actual['request_id']
    require(isinstance(request,str) and re.fullmatch(r'[A-Za-z0-9_.-]{1,128}',request)
            and request not in ('.','..'),'unsafe generation snapshot request')
    expected=root/'generation_snapshots'/request/'before'
    before=(root/snapshot).resolve(strict=True) if snapshot is not None else expected.resolve(strict=True)
    require(before==expected and expected.resolve(strict=True)==expected and root in before.parents,
            'generation snapshot request path differs')
    manifest=before.parent/'SNAPSHOT.json'
    require(str(manifest.relative_to(root)) in source_files,'unsealed generation snapshot identity')
    record=json.loads(manifest.read_text())
    require(set(record)=={'schema_version','request_id','input_checkpoint_id','input_digest','tree_sha256'}
            and isinstance(record.get('input_digest'),str)
            and re.fullmatch(r'[0-9a-f]{64}',record['input_digest']),
            'invalid generation snapshot identity')
    require(record.get('schema_version')==SNAPSHOT_SCHEMA and record.get('request_id')==request
            and record.get('input_checkpoint_id')==actual['input_checkpoint_id'],
            'generation snapshot input identity differs')
    events=[json.loads(line) for line in (root/'model_trace.jsonl').read_text().splitlines()]
    starts=[i for i,e in enumerate(events) if e.get('type')=='model_session_generation_started'
            and e.get('request_id')==request]
    require(len(starts)==1 and starts[0]>0,'generation snapshot has no unique request')
    index=starts[0];start=events[index]
    require(start.get('input_checkpoint_id')==record['input_checkpoint_id']
            and start.get('input_digest')==record.get('input_digest')
            and events[index-1]=={'type':'correction_generation_snapshot_saved',**record},
            'snapshot was not recorded immediately before the same generation')
    require(sum(e.get('type')=='correction_generation_snapshot_saved' and e.get('request_id')==request
                for e in events)==1,'duplicate generation snapshot')
    require(_tree_sha(tree_identity(before))==record.get('tree_sha256'),'generation snapshot tree differs')
    for member in before.rglob('*'):
        if member.is_file():require(str(member.relative_to(root)) in source_files,'unsealed generation snapshot member')
    return before
