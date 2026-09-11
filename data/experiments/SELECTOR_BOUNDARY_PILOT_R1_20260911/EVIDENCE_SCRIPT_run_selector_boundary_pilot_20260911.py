"""Frozen, bounded production collection for the Selector500 campaign; no role rows synthesized."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,os,signal,subprocess,sys,time
ROOT=Path('/home/chase/GitHub/RWKV-LH-selector-500-r1-20260911')
RECORD_ROOT=Path('/home/chase/GitHub/RWKV-LH')
sys.path.insert(0,str(ROOT))
ROUND=RECORD_ROOT/'data/experiments/SELECTOR_BOUNDARY_PILOT_R1_20260911'
CAMPAIGN=RECORD_ROOT/'data/experiments/SELECTOR_BOUNDARY_PILOT_R1_20260911'
BUNDLE=ROUND/'bundle'
OUTPUT=ROUND/'all_zero'
SUITE='selector500publicv1'
ZERO='0'*64
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canonical_sha(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def write(p,v):
    with p.open('x') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
def verify_bundle():
    frozen=json.loads((BUNDLE/'MANIFEST.json').read_text())
    for n,s in frozen['files'].items():assert digest(BUNDLE/n)==s,n
    assert digest(Path(frozen['campaign_registration']['path']))==frozen['campaign_registration']['sha256']
    return frozen,json.loads((BUNDLE/'tasks.json').read_text())['tasks']
def configure():
    from rwkv_lh.runtime.settings import load_local_env, reset_runtime_settings
    from rwkv_lh.supervisor_openai import SupervisorAPISettings
    from rwkv_lh.exact_tool_selector.native_network_client import NativeNetworkSelectorSettings
    from scripts import run_rwkv_e2e_benchmark as benchmark
    from benchmarks.rwkv_e2e.rwkv_execute_diagnostics_v1.audit_binding import verify_with_event_binding
    benchmark.run_isolated_verifier = verify_with_event_binding
    assert os.environ.get('WSL_DISTRO_NAME') == 'UbuntuRecovered'
    load_local_env()
    # Every role State is explicit. Ordinary deployment fields use the same
    # canonical local configuration; never override the strong Planner route.
    for role in ('EXECUTOR', 'AUDITOR_STEP', 'FINALIZER', 'AUDITOR_FINAL'):
        os.environ[f'RWKV_LH_{role}_STATE_PROFILE_ID'] = 'zero'
        os.environ[f'RWKV_LH_{role}_STATE_PROFILE_SHA256'] = ZERO
        os.environ[f'RWKV_LH_{role}_STATE_PROFILE_DELIVERY'] = 'request'
        os.environ[f'RWKV_LH_{role}_RETURN_TOKEN_IDS'] = 'true'
        os.environ[f'RWKV_LH_{role}_READ_TIMEOUT'] = '300'
    os.environ['RWKV_RUNTIME_MODE'] = 'external'
    os.environ['RWKV_EXECUTOR_PROFILE_ROUTING'] = 'disabled'
    reset_runtime_settings()
    roles = benchmark._goal_role_settings(benchmark.get_runtime_settings())
    planner = SupervisorAPISettings.from_env()
    selector = NativeNetworkSelectorSettings.from_env()
    assert planner.model == 'deepseek-v4-pro' and planner.stream_responses
    assert planner.base_url.rstrip('/') == 'https://api.deepseek.com'
    expected_options = {'thinking': {'type': 'enabled'}, 'reasoning_effort': 'low'}
    assert planner.planner_request_options == planner.stage_checker_request_options == expected_options
    assert planner.backend_profile == 'openai-compatible' and not planner.fallback_models
    assert selector is not None and selector.state_profile_id == 'zero'
    assert all(s.state_profile_id == 'zero' and s.state_profile_sha256 == ZERO for s in roles.values())
    return benchmark, roles, planner, selector


def prepare():
    from rwkv_lh.role_trace_stages import validate_collection_contract
    from rwkv_lh.stateful_goal_loop import STATEFUL_GOAL_LOOP_ARCHITECTURE
    from rwkv_lh.supervisor_openai import OpenAICompatibleSupervisorClient
    import requests
    benchmark,roles,planner,selector=configure()
    bundle,tasks=verify_bundle()
    campaign=json.loads((CAMPAIGN/'CAMPAIGN_REGISTRATION.json').read_text())
    assert len(tasks)==3
    assert not subprocess.check_output(['git','diff','--','rwkv_lh','scripts','tests','pyproject.toml','uv.lock'],cwd=ROOT)
    OUTPUT.mkdir(exist_ok=False)
    registration={'round_id':ROUND.name,'created_at':datetime.now(timezone.utc).isoformat(),
      'campaign_registration_sha256':digest(CAMPAIGN/'CAMPAIGN_REGISTRATION.json'),
      'owner_authorization':campaign['owner_authorization'],'purpose':'Selector500 independent public-task production trace collection, unchanged tested source and all-zero role States',
      'task_ids':[t['task_id'] for t in tasks],'project_families':{e['task_id']:e['project_family'] for e in bundle['task_entries']},
      'original_suites':{e['task_id']:e['suite'] for e in bundle['task_entries']},
      'source_kind':'authored public development benchmarks, actual production Agent traces; not real-user requests',
      'source_commit':'3ae1efcc','source_root':str(ROOT),'task_bundle_manifest_sha256':digest(BUNDLE/'MANIFEST.json'),
      'preregistration_sha256':digest(ROUND/'BATCH_PREREGISTRATION.json'),
      'driver_path':str(Path(__file__)),'driver_sha256':digest(Path(__file__)),
      'budgets':{'case_concurrency':1,'max_transitions_per_case':200,'case_wall_seconds':1800,'total_wall_seconds':5400,
                 'supervisor_pending_resume_attempts':0,'native_transport_resume_attempts':1,'per_case_reruns':0,
                 'strong_generation':planner.public_dict(),'rwkv_read_timeout_seconds':300},
      'role_data':{'target_role':'selector_intent','coverage_scope_sha256':digest(ROUND/'COVERAGE_SCOPE.json'),
                   'minimum_effective_train_rows_campaign':500,'minimum_independent_boundaries_campaign':167,
                   'token_ids_complete_required':True,'training_optimizer_steps_in_collection':0},
      'scope_extension':'Owner authorized additional public-task membership; original coverage-scope source description is not a task allowlist; all role coverage rules unchanged.',
      'metrics':['Strict','completed','mutation','actions','termination','role evidence','effective rows after review and fixed dedup'],
      'holdout_accessed':False}
    write(ROUND/'REGISTRATION.json',registration)
    role_health=benchmark._preflight_goal_role_runtimes(roles)
    with requests.Session() as session:
        session.trust_env=False
        response=session.get(selector.base_url.rstrip('/')+'/healthz',timeout=(5,20));response.raise_for_status();selector_health=response.json()
    assert selector_health['runtime_identity']==selector.runtime_identity()
    client=OpenAICompatibleSupervisorClient(settings=planner)
    try:planner_health=client.health()
    finally:client.close()
    assert planner_health['available'] and planner_health['model_present']
    write(OUTPUT/'runtime_doctor.json',{'roles':role_health,'selector':selector_health,'planner':planner_health,'planner_settings':planner.public_dict()})
    source=benchmark._source_tree_manifest(ROOT);write(OUTPUT/'source_tree_manifest.json',source)
    profiles={name:{'profile_id':v.state_profile_id,'profile_sha256':v.state_profile_sha256,'model_sha256':v.model_sha256} for name,v in roles.items()}
    profiles['selector_intent']={'profile_id':selector.state_profile_id,'profile_sha256':selector.state_profile_sha256,'model_sha256':selector.model_sha256}
    contract=validate_collection_contract({'mode':'role_stage','stage_id':'selector_handoff_r1','target_role':'selector_intent','profiles':profiles})
    write(OUTPUT/'RUN_PROTOCOL.json',{'schema_version':'rwkv-lh.round-run-protocol.v1','round':ROUND.name+'-all_zero',
      'architecture':STATEFUL_GOAL_LOOP_ARCHITECTURE,'suite':SUITE,'selected_case_count':len(tasks),'selected_case_ids':registration['task_ids'],
      'source_resources':[dict(suite=SUITE,role=role,path=str(BUNDLE/name),sha256=digest(BUNDLE/name)) for role,name in [('visible_tasks','tasks.json'),('hidden_acceptance','acceptance.json')]],
      'code':{'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'source_tree_manifest_sha256':canonical_sha(source),'source_tree_file_count':len(source),'runner_sha256':digest(Path(benchmark.__file__))},
      'registration_sha256':digest(ROUND/'REGISTRATION.json'),'role_data_scope_sha256':digest(ROUND/'COVERAGE_SCOPE.json'),
      'role_data_collection':contract,'budgets':registration['budgets'],'goal_role_runtimes':benchmark._goal_role_runtime_identities(roles),
      'independent_selector':{'enabled':True,'runtime_identity':selector.runtime_identity()},
      'supervisor':{'enabled':True,'settings':planner.public_dict(),'health':planner_health},
      'sampling':benchmark.LongHorizonModel._SAMPLING.to_dict(),
      'stateful_goal':benchmark.stateful_goal_protocol_metadata(enabled=True,strong_planner_available=True),
      'tokenizer':{'path':str(benchmark.VOCAB_PATH),'sha256':digest(benchmark.VOCAB_PATH)},
      'non_intervention':{'hidden_acceptance_available_during_generation':False,'final_output':'byte-exact raw RWKV response'}})
    print(json.dumps({'prepared':True,'task_ids':registration['task_ids'],'source_files':len(source),'model_requests_started':False}),flush=True)

def assert_frozen(benchmark,roles,planner,selector):
    r=json.loads((ROUND/'REGISTRATION.json').read_text());p=json.loads((OUTPUT/'RUN_PROTOCOL.json').read_text())
    assert digest(Path(__file__))==r['driver_sha256']
    assert digest(ROUND/'REGISTRATION.json')==p['registration_sha256']
    assert benchmark._source_tree_manifest(ROOT)==json.loads((OUTPUT/'source_tree_manifest.json').read_text())
    assert benchmark._goal_role_runtime_identities(roles)==p['goal_role_runtimes']
    assert planner.public_dict()==p['supervisor']['settings']
    assert selector.runtime_identity()==p['independent_selector']['runtime_identity']
    assert digest(BUNDLE/'MANIFEST.json')==r['task_bundle_manifest_sha256']
    assert digest(ROUND/'BATCH_PREREGISTRATION.json')==r['preregistration_sha256']
    verify_bundle()


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

def case(task_id):
    benchmark,roles,planner,selector=configure();assert_frozen(benchmark,roles,planner,selector)
    _,tasks=verify_bundle();task=next(t for t in tasks if t['task_id']==task_id)
    acceptance=json.loads((BUNDLE/'acceptance.json').read_text())['cases'][task_id]
    print(json.dumps({'case_started':task_id,'at':datetime.now(timezone.utc).isoformat()}),flush=True)
    install_boundary_stop(benchmark,json.loads((CAMPAIGN/'CAMPAIGN_REGISTRATION.json').read_text())['boundary_limits'][task_id])
    result=benchmark.run_case(task,acceptance,OUTPUT,max_transitions=200,supervisor_mode='openai',
       supervisor_strategy='goal_stages',independent_selector=True,supervisor_pending_resume_attempts=0,native_transport_resume_attempts=1,stateful_goal=True)
    write(OUTPUT/(task_id+'.result.json'),result);print(json.dumps(result,ensure_ascii=False),flush=True)

def collect():
    benchmark,roles,planner,selector=configure();assert_frozen(benchmark,roles,planner,selector)
    r=json.loads((ROUND/'REGISTRATION.json').read_text());started=time.monotonic();completions=[]
    write(ROUND/'STARTED.json',{'at':datetime.now(timezone.utc).isoformat(),'pid':os.getpid(),'registration_sha256':digest(ROUND/'REGISTRATION.json')})
    for task_id in r['task_ids']:
        budget=min(1800,5400-(time.monotonic()-started))
        if budget<=0:
            completions.append({'task_id':task_id,'started':False,'reason':'preregistered_total_wall_budget_exhausted'});continue
        t=time.monotonic()
        with (ROUND/(task_id+'.log')).open('x') as log:
            child=subprocess.Popen([sys.executable,str(Path(__file__)),'case','--task-id',task_id],cwd=ROOT,env=os.environ.copy(),stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            error=None
            try:code=child.wait(timeout=budget)
            except subprocess.TimeoutExpired:
                error='preregistered_wall_budget_exhausted';os.killpg(child.pid,signal.SIGTERM)
                try:child.wait(timeout=10)
                except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=10)
                code=child.returncode
        record={'task_id':task_id,'exit_code':code,'error':error,'wall_seconds':time.monotonic()-t,'result_recorded':(OUTPUT/(task_id+'.result.json')).exists()}
        completions.append(record);write(ROUND/(task_id+'.completion.json'),record);print(json.dumps(record),flush=True)
        (ROUND/'PROGRESS.json').write_text(json.dumps({'completed_workers':len(completions),'total_workers':len(r['task_ids']),'cases':completions,'optimizer_steps':0},indent=2)+'\n')
    write(ROUND/'COMPLETION.json',{'cases':completions,'wall_seconds':time.monotonic()-started,
      'source_unchanged':benchmark._source_tree_manifest(ROOT)==json.loads((OUTPUT/'source_tree_manifest.json').read_text()),'optimizer_steps':0,'ended_at':datetime.now(timezone.utc).isoformat()})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['prepare','collect','case']);p.add_argument('--task-id');a=p.parse_args()
    {'prepare':prepare,'collect':collect,'case':lambda:case(a.task_id)}[a.phase]()
