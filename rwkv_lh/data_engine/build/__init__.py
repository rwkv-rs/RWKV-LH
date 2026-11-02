"""Seal passing product transcripts in the exact upstream layout dataset.py reads."""
import hashlib
import json
from pathlib import Path
from rwkv_lh.project_ledger import ProjectLedger
from rwkv_lh.project_protocols import agent
from rwkv_lh.project_runtime import agent_definitions
from rwkv_lh.harness import ActionHarness
from rwkv_lh.project_trace import agent_boundaries
from rwkv_lh.transcript.frozen import training_messages, validate_row_acceptance, ACCEPTANCE_SCHEMA
from rwkv_lh.transcript.tokenize import tokenize_transcript
from rwkv_lh.transcript.export import session_transcript
from rwkv_lh.tokenizer import RWKVTokenizer
from rwkv_lh.token_budget import VOCAB_PATH
from rwkv_lh.workspace_snapshot import tree_identity
from rwkv_lh.data_engine.tasks import dump,checksum
from rwkv_lh.data_engine.records import write_immutable
from rwkv_lh.evaluation_policy import assert_training_record_allowed, assert_training_source_allowed


def export_episode(task, run, verdict, production_root, export_root, *, teacher, context_tokens=65536):
    run,production_root,export_root=map(Path,(run,production_root,export_root))
    assert_training_record_allowed(task)
    for path in (run, production_root, export_root):
        assert_training_source_allowed(path)
    if verdict['task_digest']!=task['digest'] or verdict['passed'] is not True: raise ValueError('passing real execution required')
    if tree_identity(run/'workspace')!=verdict['workspace']:raise ValueError('workspace changed after verification')
    with ProjectLedger.read_snapshot(run/'execution') as db:
        tip=db.scan_verified_events();state=tip['state']
    if state['pending'] or state['inbox'] or state['status']!='finished':raise ValueError('finished confirmed execution required')
    # Reconstruct every boundary through the production builder before publishing.
    boundaries=list(agent_boundaries(run/'execution'))
    if not boundaries:raise ValueError('missing actual execution boundaries')
    definitions=agent_definitions(ActionHarness())
    exported=session_transcript(run/'execution',definitions)
    document=json.loads(exported['bytes'])
    messages=document['messages']
    messages=training_messages(messages,definitions)
    encoded=tokenize_transcript(messages,tokenizer=RWKVTokenizer(VOCAB_PATH),native_tools=definitions,max_tokens=context_tokens)
    episode=run.name
    acceptance={'schema_version':ACCEPTANCE_SCHEMA,'run_id':episode,'verifier_sha256':verdict['verifier_sha256'],
        'verifiable':True,'passed':True,'checks':{f'check_{i:03d}_{v["kind"]}':v['passed'] for i,v in enumerate(verdict['checks'])}}
    validate_row_acceptance(acceptance,episode_id=episode)
    raw=exported['bytes'];sha=exported['sha256']
    target=production_root/episode
    write_immutable(target/'native_messages.json',raw)
    provenance={'task':{'id':task['id'],'family':task['family'],'digest':task['digest'],
        'prompt':task['request'],'defect_family':str(task.get('workflow',task['family']))},'source':task['source'],
        'teacher':teacher,'ledger_tip':tip['digest'],'verification_sha256':checksum(verdict),
        'input_tokens':len(encoded['input_ids']),'supervised_tokens':sum(encoded['loss_mask']),
        'protocol_source_sha256':hashlib.sha256(Path(agent.__file__).read_bytes()).hexdigest(),
        'policy':'round0_teacher_in_production_loop','rollout_policy':'qwen','training_eligible':True}
    write_immutable(target/'freeze.json',dump(provenance).encode())
    write_immutable(target/'manifest.json',dump({'native_messages.json':sha,'freeze.json':hashlib.sha256((target/'freeze.json').read_bytes()).hexdigest()}).encode())
    # One immutable export shard per episode avoids shared JSONL append races.
    shard=export_root/episode
    write_immutable(shard/'native_messages.json',raw)
    write_immutable(shard/'sources.json',dump({'origin':'production','files':[{'path':'native_messages.json','sha256':sha}]}).encode())
    write_immutable(shard/'train.jsonl',(json.dumps({'episode_id':episode,'source':sha,'acceptance':acceptance},ensure_ascii=False)+'\n').encode())
    return {'episode_id':episode,'source':sha,'input_tokens':len(encoded['input_ids']),'supervised_tokens':sum(encoded['loss_mask']),'shard':str(shard)}
