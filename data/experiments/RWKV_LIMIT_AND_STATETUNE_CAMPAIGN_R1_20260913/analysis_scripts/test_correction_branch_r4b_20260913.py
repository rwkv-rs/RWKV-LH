import json
from pathlib import Path
from rwkv_lh.schema import RunState,CausalEventDraft
from rwkv_lh.store import LongHorizonStore

def test_original_checkpoint_branch_uses_registered_causal_type(tmp_path):
 source=Path('/home/chase/GitHub/RWKV-LH/data/experiments/RWKV_SUMMARY_ADVICE_DIAGNOSTIC_R3_20260913/runs/trial-2/pre_advice_state.json')
 s=RunState.from_dict(json.loads(source.read_text()));store=LongHorizonStore(tmp_path/'state');saved=store.save(s,expected_revision=-1,causal_event=CausalEventDraft.create('run_created',{'goal_digest':s.goal.digest,'source_snapshot':str(source)},subject_id=s.run_id));loaded=store.load(saved.run_id)
 assert loaded.lane_head('executor')==s.lane_head('executor')
 assert loaded.model_states[s.lane_head('executor')].native_state_digest==s.model_states[s.lane_head('executor')].native_state_digest
