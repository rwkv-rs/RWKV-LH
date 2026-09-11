from pathlib import Path
import json, hashlib, importlib
root=Path('/home/chase/GitHub/RWKV-LH')
p=root/'tests/test_goal_state_protocols.py'
s=p.read_text().replace('(\"selector-intent\", \"v6\")','("selector-intent", "v7")').replace('(\"executor-args\", \"v6\")','("executor-args", "v7")').replace('(\"auditor-step\", \"v6\")','("auditor-step", "v7")').replace('(\"finalizer-answer\", \"v2\")','("finalizer-answer", "v3")').replace('(\"auditor-final\", \"v4\")','("auditor-final", "v5")').replace('(".v7", ".v8", ".v999")','(".v8", ".v999")').replace('auditor_step_v7.REASON_COMPLETE','"The requested file contents are present in A1."').replace('auditor_final.REASON_READY','"The answer agrees with the observed value in A1."')
p.write_text(s)
p=root/'tests/test_stateful_goal_loop.py'
s=p.read_text().replace('assert len(refs) == root_count + 1','assert refs == action_ids').replace('test_clean_executor_turn_reduces_causal_facts_to_fit_input_budget','test_clean_executor_turn_blocks_without_discarding_required_facts')
a=s.index('    checkpoint = model._start_clean_executor_turn(',s.index('def test_clean_executor_turn_blocks'))
b=s.index('\n\ndef test_stateful_input_budget',a)
s=s[:a]+'''    with pytest.raises(InputBudgetError, match="injected count 12"):
        model._start_clean_executor_turn(
            state,
            previous,
            lambda _state, event_type, payload: persisted.append((event_type, dict(payload))),
            fact_action_ids=fact_action_ids,
        )
    assert attempted_counts == [12]
    assert state.lane_heads["executor"] == previous.checkpoint_id
    assert persisted == []
'''+s[b:]
p.write_text(s)
p=root/'rwkv_lh/stateful_goal_loop.py'
s=p.read_text().replace('fresh Selector Intent v6','fresh Selector Intent v7').replace('"causal_fact_reduction_exhausted": True','"required_evidence_discarded": False')
p.write_text(s)
p=root/'data/test_fixtures/controller_role_closure_v1/role_prompt_wire_baseline.json'
data=json.loads(p.read_text())
data['source_kind']='existing_public_unit_test_inputs_rerendered_for_role_information_flow_r1'
data['source_test_sha256']=hashlib.sha256((root/data['source_test_path']).read_bytes()).hexdigest()
data['capture_script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
for record in data['records']:
    module=importlib.import_module('rwkv_lh.goal_state_protocols.'+record['protocol'])
    source=module.build_prompt_source(**record['arguments'])
    record['prompt']=module.render_prompt(source)
    record['source_sha256']=hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
