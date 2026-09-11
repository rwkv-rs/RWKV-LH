"""Exercise the collection stop adapter without constructing any role protocol input."""
from pathlib import Path
from types import SimpleNamespace
import importlib.util,json
R=Path('/home/chase/GitHub/RWKV-LH')
p=R/'temp/run_selector_boundary_pilot_20260911.py'
spec=importlib.util.spec_from_file_location('boundary_driver',p);driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
results=[]
for limit in (1,2,3):
    actions=[]
    state=SimpleNamespace(causal_records={},causal_order=[])
    class Base:
        def _persist_callback(self,state,event_type,event):
            key=str(len(state.causal_order));state.causal_records[key]=SimpleNamespace(event_type=event_type,payload=event);state.causal_order.append(key)
        def run(self,run_id):
            for i in range(4):
                self._persist_callback(state,'unrelated',{})
                self._persist_callback(state,'exact_tool_selection_staged',{'selection_id':str(i)})
                actions.append(i)
            raise AssertionError('Requested durable collection boundary was not honored')
        def _yield(self,state,reason,transitions):
            self._persist_callback(state,'run_yielded',{'reason':reason})
            return SimpleNamespace(state=state,transitions=transitions)
    def unexpected_resume(*args,**kwargs):raise AssertionError('Collection boundary incorrectly resumed')
    bench=SimpleNamespace(StatefulGoalLoopController=Base,_continue_stateful_goal_within_budget=unexpected_resume)
    driver.install_boundary_stop(bench,limit)
    value=bench.StatefulGoalLoopController().run('test')
    assert len(actions)==limit-1
    assert sum(e.event_type=='exact_tool_selection_staged' for e in state.causal_records.values())==limit
    assert bench._continue_stateful_goal_within_budget(value,max_total_transitions=200,resume=unexpected_resume)==(value,0,0)
    assert state.causal_records[state.causal_order[-1]].payload['reason']=='selector_collection_boundary_reached'
    results.append({'limit':limit,'prior_downstream_actions':len(actions),'boundary_durable':True,'no_post_boundary_action_or_resume':True})
out=R/'data/experiments/SELECTOR_BOUNDARY_PILOT_R1_20260911/ADAPTER_CONTRACT_CHECK.json'
with out.open('x') as f:json.dump({'cases':results,'passed':len(results),'model_calls':0,'role_protocol_inputs_synthesized':False},f,indent=2);f.write('\n')
print('3 adapter boundary checks passed')
