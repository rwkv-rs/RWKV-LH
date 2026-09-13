from pathlib import Path
import sys, json, time, shutil, signal, traceback
from dataclasses import replace
R=Path('/home/chase/GitHub/RWKV-LH'); D=R/'data/experiments/RWKV_FEEDBACK_TASK_BASELINE_R1_20260913';sys.path.insert(0,str(D/'source'))
from rwkv_lh import task_review as review
from rwkv_lh.runtime.settings import get_runtime_settings,load_local_env
from rwkv_lh.model import LongHorizonModel
from rwkv_lh.model_session import create_model_session
from rwkv_lh.harness import ActionHarness
from rwkv_lh.controller import LongHorizonController
from rwkv_lh.store import LongHorizonStore
from rwkv_lh.schema import RunStatus
from rwkv_lh.run_lifecycle import RUN_LIFECYCLE_POLICY_KEY,run_lifecycle_policy_document

class TrialBudgetExpired(TimeoutError): pass
class ReadOnlyController(LongHorizonController):
    # Permission check only. Production run() constructs feedback and chooses no business arguments.
    def _execute_decision(self,state,decision):
        definition=self.harness.definition(decision.command.name)
        if not definition.read_only or definition.side_effect:
            raise PermissionError('registered read-only scope: operation not permitted')
        return super()._execute_decision(state,decision)

def save(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def inventory(root):
    return {str(p.relative_to(root)):review.file_digest(p) for p in sorted(root.rglob('*')) if p.is_file()}
def deadline(signum,frame): raise TrialBudgetExpired('registered wall budget exhausted')
def run():
    reg=json.loads((D/'REGISTRATION.json').read_text())
    assert review.file_digest(Path(__file__))==reg['runner_sha256']
    assert all(review.file_digest(D/'source'/p)==sha for p,sha in reg['source_pins'].items())
    load_local_env(R/'.env.local')
    settings=replace(get_runtime_settings(),base_url=reg['base_url'],model=reg['model_name'],model_sha256=reg['model_sha256'],tool_disclosure_mode='full',return_token_ids=True,state_transport='native_required',state_profile_id='zero',state_profile_sha256='0'*64,read_timeout_seconds=180)
    assert LongHorizonModel._SAMPLING.to_dict()==reg['sampling']
    results=[];global_started=time.monotonic();global_calls=0
    signal.signal(signal.SIGALRM,deadline)
    for repeat in (1,2):
        for case in reg['cases']:
            p=D/'runs'/f'{case["id"]}-feedback-r{repeat}';p.mkdir(parents=True,exist_ok=False)
            src=R/case['workspace_source'];assert inventory(src)==case['workspace_sha256'];shutil.copytree(src,p/'workspace')
            calls=0
            def audit(event):
                nonlocal calls,global_calls
                if event['type']=='model_session_generation_started':
                    if calls>=6 or global_calls>=48: raise TrialBudgetExpired('registered model call budget exhausted')
                    calls+=1;global_calls+=1
                with (p/'model_trace.jsonl').open('a') as stream:stream.write(json.dumps(dict(event),ensure_ascii=False)+'\n')
            harness=ActionHarness();model=LongHorizonModel(create_model_session(settings=settings,audit_hook=audit),harness=harness)
            store=LongHorizonStore(p/'state',checkpoint_retention=1000)
            goal=model.create_literal_goal(case['request'],str(p/'workspace'),runtime_policy={RUN_LIFECYCLE_POLICY_KEY:run_lifecycle_policy_document('goal')})
            state=store.create_run(goal,run_id=p.name);controller=ReadOnlyController(store,model=model,harness=harness,max_transitions=6,min_actions=0)
            save(p/'goal.json',goal.to_dict());started=time.monotonic();error=None;termination=None
            try:
                remaining=min(300,3000-(time.monotonic()-global_started))
                if remaining<=0: raise TrialBudgetExpired('registered batch wall budget exhausted')
                signal.setitimer(signal.ITIMER_REAL,remaining)
                result=controller.run(p.name);state=result.state
            except Exception as exc:
                error={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
                termination=type(exc).__name__;state=store.load(p.name)
                controller._persist(state,'run_interrupted',{'reason':termination,'final_output':'','controller_rewritten':False})
            finally:
                signal.setitimer(signal.ITIMER_REAL,0)
            state=store.load(p.name)
            terminal=[state.causal_records[k] for k in state.causal_order if state.causal_records[k].event_type in ('run_completed','run_interrupted','run_yielded')]
            save(p/'terminal_records.json',[x.to_dict() for x in terminal])
            if termination is None:
                termination='submitted' if state.status==RunStatus.COMPLETED else 'budget'
            row={'id':p.name,'file_id':case['id'],'arm':'feedback','repeat':repeat,'final':state.final_output or None,'termination':termination,'error':error,'actions':[a.to_dict() for a in state.actions.values()],'elapsed_seconds':time.monotonic()-started,'workspace_unchanged':inventory(p/'workspace')==case['workspace_sha256'],'generation_started':calls,'status':state.status.value,'terminal_reasons':[e.payload.get('reason') for e in terminal]}
            save(p/'state_snapshot.json',state.to_dict());save(p/'RESULT.json',row);results.append(row);save(D/'RESULTS.json',results)
            print(p.name,termination,'calls',calls,flush=True)
            if error and termination!='TrialBudgetExpired':break
        if error and termination!='TrialBudgetExpired':break
if __name__=='__main__':run()
