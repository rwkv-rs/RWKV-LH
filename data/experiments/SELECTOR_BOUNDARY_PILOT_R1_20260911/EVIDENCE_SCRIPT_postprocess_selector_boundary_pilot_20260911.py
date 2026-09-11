"""Verify completed production cases and prepare auditable Selector rows; never approve labels."""
from pathlib import Path
import collections,hashlib,json,re,shutil,sys,time,traceback
R=Path('/home/chase/GitHub/RWKV-LH');W=Path('/home/chase/GitHub/RWKV-LH-selector-500-r1-20260911')
sys.path.insert(0,str(W))
from rwkv_lh.goal_state_protocols.role_trace_dataset_v1 import register_case,load_source_run,extract_registration
from rwkv_lh.role_trace_inputs import rebuild_role_input
from rwkv_lh.role_trace_context import reconstruct_context,bind_server_input_tokens
O=R/'data/experiments/SELECTOR_BOUNDARY_PILOT_R1_20260911'
V=R/'data/experiments/SELECTOR_BOUNDARY_REVIEW_R1_20260911'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,value):
    with p.open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')

deadline=time.monotonic()+22000
while not (O/'COMPLETION.json').exists():
    if time.monotonic()>deadline:raise TimeoutError('Registered batch did not publish completion; no invented results')
    time.sleep(10)
completion=json.loads((O/'COMPLETION.json').read_text())
assert completion['source_unchanged'], 'Frozen collection source changed'
registration=json.loads((O/'REGISTRATION.json').read_text());protocol=json.loads((O/'all_zero/RUN_PROTOCOL.json').read_text())
scope=O/'COVERAGE_SCOPE.json'
sources=None;excluded=[];agent=[]
for task_id in registration['task_ids']:
    result_path=O/'all_zero'/(task_id+'.result.json')
    if not result_path.exists():
        excluded.append({'case':task_id,'reason':'missing_completed_case_artifacts'});agent.append({'case':task_id,'result_recorded':False});continue
    result=json.loads(result_path.read_text());audit=json.loads((O/'all_zero/cases'/task_id/'audit.json').read_text())
    actions=list(audit['action_ledger'].values());ended=[a for a in actions if a['status'] in ('succeeded','failed')]
    valid=lambda s:isinstance(s,str) and re.fullmatch('[0-9a-f]{64}',s) is not None
    unknown=sum(not(valid(a.get('workspace_digest_before')) and valid(a.get('workspace_digest_after'))) for a in ended)
    mutations=sum(a['status']=='succeeded' and valid(a.get('workspace_digest_before')) and valid(a.get('workspace_digest_after')) and a['workspace_digest_before']!=a['workspace_digest_after'] for a in actions)
    reasons=[(e.get('data') or {}).get('reason') for e in audit['events'] if e.get('type')=='run_blocked']
    agent.append({'case':task_id,'result_recorded':True,'Strict':bool(result['passed']),'completed':bool(result['agent_completed']),
                  'external_passed':bool(result['external_passed']),'actions':len(actions),'mutation_count':mutations if not unknown else None,
                  'mutation_digest_unknown':unknown,'termination':reasons[-1] if reasons else result['status']})
    try:
        current=register_case(O/'all_zero/cases'/task_id,run_id=task_id,source_run_id=protocol['round'],
                              project_family=registration['project_families'][task_id],suite=protocol['suite'])
        record=current['source_runs'][0];source=load_source_run(record,base_dir=O,coverage_scope_sha256=sha(scope))
        verified=[];starts={r['request_id']:r for r in source.model_trace if r.get('type')=='model_session_generation_started'}
        for returned in source.model_trace:
            if returned.get('type')!='model_session_generation_returned':continue
            start=starts[returned['request_id']]
            context=reconstruct_context(start['input_checkpoint_id'],source.final_state.model_states,source.model_trace)
            checked=bind_server_input_tokens(context,returned['raw_generation']);assert checked['token_ids_complete']
            verified.append({'kind':'generation_context','role':returned['model_role'],'request_id':returned['request_id'],
                             'full_input_token_match':True,'input_tokens':len(checked['token_ids']),'finish_reason':returned['finish_reason']})
        for event in source.final_state.causal_records.values():
            if event.event_type=='tool_schema_disclosed':role='executor_args'
            elif event.event_type=='goal_auditor_session_started':role=event.payload['auditor_role']
            elif event.event_type=='goal_finalizer_session_started':role='finalizer_answer'
            else:continue
            rebuilt=rebuild_role_input(role,source.snapshots[event.event_id],{'boundary_event_id':event.event_id,'checkpoint_id':event.payload['checkpoint_id']})
            actual=source.snapshots[event.event_id].model_states[event.payload['checkpoint_id']].transcript
            assert rebuilt['expected_checkpoint_transcript']==actual
            if role in ('executor_args','auditor_step'):assert rebuilt['prompt_source']['immutable_goal']==source.final_state.goal.request
            verified.append({'kind':'role_input','role':role,'event_id':event.event_id,'production_rebuild_exact':True})
        write(O/(task_id+'.HANDOFF_VERIFICATION.json'),{'case':task_id,'all_verified':True,'rows':verified,
               'generation_contexts':sum(v['kind']=='generation_context' for v in verified),
               'role_inputs':sum(v['kind']=='role_input' for v in verified),'script_sha256':sha(Path(__file__))})
        if sources is None:sources=current
        else:sources['source_runs'].extend(current['source_runs'])
    except Exception as exc:
        excluded.append({'case':task_id,'reason':'source_or_handoff_integrity_failure','error_type':type(exc).__name__,'error':str(exc)})
        write(O/(task_id+'.HANDOFF_FAILURE.json'),{'error':str(exc),'traceback':traceback.format_exc()})
write(O/'SOURCE_ADMISSION_EXCLUSIONS.json',excluded)
known=[a for a in agent if a['result_recorded']]
write(O/'AGENT_SUMMARY.json',{'planned_cases':len(agent),'recorded_cases':len(known),'Strict':sum(a['Strict'] for a in known),
 'completed':sum(a['completed'] for a in known),'actions':sum(a['actions'] for a in known),
 'mutation_count':sum(a['mutation_count'] for a in known) if all(a['mutation_count'] is not None for a in known) else None,
 'cases':agent,'optimizer_steps':0,'scores_recomputed':False})
assert sources is not None, 'No admissible production sources'
sources['coverage_scope']={'path':str(scope),'sha256':sha(scope)}
path=O/'FRESH_SOURCE_REGISTRATION.json';write(path,sources)
out=W/'data/experiments/SELECTOR_BOUNDARY_PILOT_R1_20260911/fresh_selector_candidates'
manifest=extract_registration(path,out,roles=['selector_intent']);shutil.copytree(out,O/'fresh_selector_candidates')
queue=O/'fresh_selector_candidates/review_queue.jsonl';rows=[json.loads(line) for line in queue.read_text().splitlines()]
write(O/'FRESH_EXTRACTION_RESULT.json',{'sources':len(sources['source_runs']),'raw_candidates':manifest['row_count'],
 'pending_review':len(rows),'status':manifest['status'],'coverage':manifest['coverage_audit'],'gates':manifest['quality_gates'],
 'no_waiver':True,'not_final_effective_count':True,'first_case_preview_not_counted_again':True,'optimizer_steps':0})
V.mkdir(exist_ok=False);groups=collections.defaultdict(list)
for row in rows:groups[(row['source_run_id'],row['run_id'],row['boundary_event_id'])].append(row)
index=[]
for n,(identity,group) in enumerate(sorted(groups.items()),1):
    assert len({json.dumps(r['protocol_source'],sort_keys=True) for r in group})==1
    packet={'packet_id':f'B{n:03d}','source_run_id':identity[0],'run_id':identity[1],'boundary_event_id':identity[2],
      'protocol_source':group[0]['protocol_source'],
      'rows':[{k:r.get(k) for k in ('sample_id','request_id','original_target_text','original_output_record_sha256','available_evidence_refs','split')}
              |{'input_sha256':hashlib.sha256(r['input_text'].encode()).hexdigest()} for r in group]}
    file=V/(packet['packet_id']+'.json');write(file,packet)
    index.append({'packet_id':packet['packet_id'],'run_id':identity[1],'boundary':identity[2],'rows':len(group),
                  'path':str(file),'sha256':sha(file),'subtask':group[0]['protocol_source']['current_subtask']})
write(V/'MANIFEST.json',{'source_path':str(queue),'source_sha256':sha(queue),'row_count':len(rows),'boundary_count':len(groups),'packets':index,
 'authorization':'Owner authorized two independent AI Selector semantic reviewers; Selector500 campaign preserves that authorization.',
 'rule':'Review every row using only source-visible evidence. Accept original, explicit eligible correction, or reject ambiguous/unsupported. No fabricated evidence or automatic training approval.',
 'independence':'No reading other reviewer decisions before submission; disagreements excluded.','optimizer_steps':0})
print(json.dumps({'postprocessing_complete':True,'sources':len(sources['source_runs']),'raw_candidates':manifest['row_count'],
                  'review_rows':len(rows),'review_boundaries':len(groups),'exclusions':excluded}),flush=True)
