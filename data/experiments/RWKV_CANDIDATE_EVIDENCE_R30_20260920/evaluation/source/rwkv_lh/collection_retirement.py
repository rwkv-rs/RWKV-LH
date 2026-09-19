"""Explicit retirement of sealed collection runs, never implicit HTTP-client GC.

Original traces remain immutable. Retired exports cannot resume by old handle;
verified full inputs and generation workspace snapshots remain for fresh replay.
"""
import hashlib
import json
from pathlib import Path

from .collection_conversion import export_boundaries
from .collection_execution import service_fingerprint


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tree(root):
    paths=list(Path(root).rglob('*'))
    if any(p.is_symlink() for p in paths):
        raise ValueError('symlink evidence cannot be retired')
    return {str(p.relative_to(root)):digest(p) for p in paths if p.is_file()}


def require_terminal(root):
    state=json.loads((Path(root)/'state_snapshot.json').read_text())
    result_path=Path(root)/'RESULT.json'
    if not result_path.is_file():
        raise ValueError('active or unknown run cannot be retired without terminal result')
    result=json.loads(result_path.read_text())
    if (result.get('id')!=state.get('run_id') or not result.get('id')
            or result.get('trace_complete') is not True
            or result.get('status') not in {'completed','interrupted','failed','blocked'}
            or result.get('termination') not in {'submitted','budget','error'}):
        raise ValueError('active or unverified execution cannot be retired')
    return state


def seal_run(root, output, model_sha256, *, expected_state_profile=None):
    require_terminal(root)
    if expected_state_profile is None:
        return export_boundaries(root,model_sha256,output)
    return export_boundaries(root,model_sha256,output,expected_state_profile=expected_state_profile)


def prepare_retirement(root, evidence, *, expected_service):
    root,evidence=Path(root).resolve(),Path(evidence).resolve()
    manifest=json.loads((evidence/'MANIFEST.json').read_text())
    if (manifest.get('run_root')!=str(root)
            or manifest.get('source_files')!=tree(root)
            or not (evidence/'boundaries.jsonl').is_file()
            or manifest.get('boundaries_sha256')!=digest(evidence/'boundaries.jsonl')):
        raise ValueError('sealed evidence changed or missing')
    state=require_terminal(root)
    identities={}
    for cp in state['model_states'].values():
        exported=cp.get('native_state_export') or {}
        if not exported:
            continue
        if cp.get('status')!='committed':
            raise ValueError('uncommitted checkpoint requires explicit rollback')
        if any(exported.get(k)!=expected_service[k] for k in ('model','server_build','tokenizer_build')):
            raise ValueError('checkpoint belongs to a different service')
        identity={k:exported[k] for k in ('state_ref','state_digest','cache_binding_digest')}
        ref=identity['state_ref']
        if ref in identities and identities[ref]!=identity:
            raise ValueError('conflicting checkpoint identity')
        identities[ref]=identity
    plan={'run_root':str(root),'manifest_sha256':digest(evidence/'MANIFEST.json'),
          'service':expected_service,'states':list(identities.values()),
          'resume_policy':'old native handles retired; fresh verified input replay required'}
    # Write the irreversible lifecycle decision BEFORE sending a mutation.
    pending=evidence/'RETIREMENT_PLAN.json'
    if pending.exists() and json.loads(pending.read_text())!=plan:
        raise ValueError('retirement plan changed')
    if not pending.exists():
        with pending.open('x') as f:
            json.dump(plan,f,indent=2);f.flush()
            import os
            os.fsync(f.fileno())
    return plan


def release_sealed_run(root, evidence, client, *, expected_service):
    return release_sealed_runs([(root,evidence)],client,expected_service=expected_service)[0]


def release_sealed_runs(runs, client, *, expected_service):
    if service_fingerprint(client.settings)!=expected_service:
        raise ValueError('retirement service identity differs')
    plans=[prepare_retirement(root,evidence,expected_service=expected_service) for root,evidence in runs]
    identities={}
    for plan in plans:
        for identity in plan['states']:
            ref=identity['state_ref']
            if ref in identities and identities[ref]!=identity:
                raise ValueError('conflicting State identity across runs')
            identities[ref]=identity
    outcome=client.state_release(states=list(identities.values()),release_import_aliases=True) if identities else {'released_state_refs':[]}
    if set(outcome.get('released_state_refs',[]))!=set(identities):
        raise ValueError('incomplete State retirement receipt')
    results=[]
    for (_,evidence),plan in zip(runs,plans):
        evidence=Path(evidence)
        # All runs bind the real service response, including any alias retirement.
        result={'plan_sha256':digest(evidence/'RETIREMENT_PLAN.json'),'result':outcome}
        temporary=evidence/'RETIREMENT_RESULT.pending'
        temporary.write_text(json.dumps(result,indent=2)+'\n')
        temporary.replace(evidence/'RETIREMENT_RESULT.json')
        results.append(result)
    return results
