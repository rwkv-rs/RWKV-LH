from pathlib import Path
import hashlib,json,shutil
R=Path('/home/chase/GitHub/RWKV-LH');E=R/'data/experiments'
old=E/'SELECTOR_500_CAMPAIGN_R1_20260911';first=E/'SELECTOR_500_BATCH01_20260911'
O=E/'SELECTOR_BOUNDARY_BATCH01_20260911';O.mkdir(exist_ok=False);B=O/'bundle';B.mkdir()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return {'path':str(p),'sha256':sha(p)}
def write(p,d):
    with p.open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n')
queue=json.loads((old/'TASK_QUEUE.json').read_text());entries=queue[27:39]
assert not (E/'SELECTOR_500_BATCH03_20260911/STARTED.json').exists()
campaign=json.loads((old/'REGISTRATION.json').read_text())
campaign.update(campaign_id=O.name,owner_authorization='Owner explicitly requested Selector-specific production boundary collection on2026-09-11; stop full Agent collection and collect later roles only after upstream State qualification.',
 stop='Stop immediately after durable Nth exact_tool_selection_staged; N=1,2,3 cyclically by fixed original queue position. No scoring-based stop or task selection.',
 queued_task_count=12,maximum_campaign_model_seconds=21600,pilot_only=False,
 boundary_limits={e['task_id']:(i%3)+1 for i,e in enumerate(entries)},
 task_queue=ref(old/'TASK_QUEUE.json'),legacy_campaign_ref=ref(old/'REGISTRATION.json'),
 qualification=['durable full three-menu Selector evidence','no downstream generation after selected boundary','unchanged exact production input/token replay','existing extractor queues or admits Selector rows','stopped runs are not completed Agent successes'],
 agent_scores_not_acceptance_metric=True,production_source_changes=False,
 continuation_after_pilot='First12-task expansion after validated3-task pilot; no whole-Agent continuation;500 still requires reviewed deduped train rows')
campaign['boundary_mechanism_gate']={'path': '/home/chase/GitHub/RWKV-LH/data/experiments/SELECTOR_BOUNDARY_PILOT_R1_20260911/BOUNDARY_MECHANISM_GATE.json', 'sha256': 'aa29fbc775f93038f14b0cbdc7558ab2c5ba48cbfb0ee8ae139e804ed2464b14'}
write(O/'CAMPAIGN_REGISTRATION.json',campaign)
write(B/'tasks.json',{'schema_version':'rwkv-selector-500-collection.tasks.v1','tasks':[e['task'] for e in entries]})
write(B/'acceptance.json',{'schema_version':'rwkv-selector-500-collection.acceptance.v1','cases':{e['task_id']:e['acceptance'] for e in entries}})
write(B/'MANIFEST.json',{'files':{n:sha(B/n) for n in ['tasks.json','acceptance.json']},'campaign_registration':ref(O/'CAMPAIGN_REGISTRATION.json'),
 'task_entries':[{'suite':e['suite'],'task_id':e['task_id'],'project_family':e['project_family']} for e in entries]})
shutil.copyfile(first/'COVERAGE_SCOPE.json',O/'COVERAGE_SCOPE.json')
write(O/'BATCH_PREREGISTRATION.json',{'campaign':ref(O/'CAMPAIGN_REGISTRATION.json'),'source_commit':'3ae1efcc',
 'task_ids':[e['task_id'] for e in entries],'bundle':ref(B/'MANIFEST.json'),'fixed_original_queue_slice':[27,39],
 'boundary_limits':campaign['boundary_limits'],'no_source_model_prompt_or_protocol_changes':True,'max_wall_seconds':21600,
 'case_wall_seconds':1800,'task_selection_uses_scores':False,'optimizer_steps':0})
driver=(first/'EVIDENCE_SCRIPT_run_selector_500_batch01_20260911.py').read_text()
driver=driver.replace('SELECTOR_500_BATCH01_20260911',O.name).replace('SELECTOR_500_CAMPAIGN_R1_20260911',O.name)
driver=driver.replace("CAMPAIGN/'REGISTRATION.json'","CAMPAIGN/'CAMPAIGN_REGISTRATION.json'")
driver=driver
hook='''
def install_boundary_stop(benchmark, limit):
    """Wrap only the durable event callback; production inference is inherited unchanged."""
    original=benchmark.StatefulGoalLoopController
    original_continue=benchmark._continue_stateful_goal_within_budget
    class BoundaryReached(BaseException):
        def __init__(self,state):self.state=state
    class BoundedController(original):
        def _persist_callback(self,state,event_type,event):
            super()._persist_callback(state,event_type,event)
            if event_type=='exact_tool_selection_staged':
                count=sum(e.event_type==event_type for e in state.causal_records.values())
                if count>=limit:raise BoundaryReached(state)
        def run(self,run_id):
            try:return super().run(run_id)
            except BoundaryReached as reached:
                # No completed action transition after this selection. This adapter's
                # result is a collection yield, not an end-to-end transition score.
                return self._yield(reached.state,'selector_collection_boundary_reached',0)
    def continue_collection(initial,**kwargs):
        events=initial.state.causal_records
        latest=events[initial.state.causal_order[-1]] if initial.state.causal_order else None
        if latest and latest.event_type=='run_yielded' and latest.payload.get('reason')=='selector_collection_boundary_reached':
            return initial,0,0
        return original_continue(initial,**kwargs)
    benchmark.StatefulGoalLoopController=BoundedController
    benchmark._continue_stateful_goal_within_budget=continue_collection

'''
driver=driver.replace('def case(task_id):',hook+'def case(task_id):')
needle="    result=benchmark.run_case(task,acceptance,OUTPUT,max_transitions=200,supervisor_mode='openai',"
assert needle in driver
driver=driver.replace(needle,"    install_boundary_stop(benchmark,json.loads((CAMPAIGN/'CAMPAIGN_REGISTRATION.json').read_text())['boundary_limits'][task_id])\n"+needle)
path=R/'temp/run_selector_boundary_batch01_20260911.py';path.write_text(driver)
shutil.copyfile(path,O/('EVIDENCE_SCRIPT_'+path.name))
post=(first/'EVIDENCE_SCRIPT_postprocess_selector_500_batch01_20260911.py').read_text().replace('SELECTOR_500_BATCH01_20260911',O.name).replace('SELECTOR_500_REVIEW_BATCH01_20260911','SELECTOR_BOUNDARY_REVIEW_BATCH01_20260911')
postpath=R/'temp/postprocess_selector_boundary_batch01_20260911.py';postpath.write_text(post)
shutil.copyfile(postpath,O/('EVIDENCE_SCRIPT_'+postpath.name))
write(O/'POSTPROCESS_REGISTRATION.json',{'script_path':str(postpath),'script_sha256':sha(postpath),'actual_production_extractor':True,'no_label_acceptance':True,'optimizer_steps':0})
print(json.dumps({'task_ids':campaign['boundary_limits'],'driver':str(path)}))
