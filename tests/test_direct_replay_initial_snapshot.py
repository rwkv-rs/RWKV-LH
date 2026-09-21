from pathlib import Path
import json,tarfile
import pytest
R=Path(__file__).resolve().parents[1];ARCHIVE=R/'data/test_fixtures/source_bound_regressions/RWKV_REPLAY_INITIAL_SNAPSHOT_R1_20260915_REAL_TRACE_FIXTURES.tar.gz';MODEL='559371f5b9aef13189ae54b345ac096af4ad2b689996c05d89de687612b3ae65'
def replay(root):
 from rwkv_lh.direct_trace_data import replay_run
 return replay_run(root,MODEL)
def fixture(tmp_path,name):
 with tarfile.open(ARCHIVE) as tar:tar.extractall(tmp_path,filter='data')
 return tmp_path/name
@pytest.mark.parametrize('name',['backup-snapshot','timebook-add'])
def test_replay_uses_real_initial_snapshot_after_workspace_writes(tmp_path,name):
 root=fixture(tmp_path,name);rows=replay(root);events=[json.loads(l) for l in (root/'model_trace.jsonl').read_text().splitlines()];gens=[e for e in events if e['type']=='model_session_generation_returned']
 assert len(rows)==len(gens)
 for g in gens:
  r=rows[g['candidate_checkpoint_id']];assert r['input_token_ids']==g['raw_generation']['prompt_token_ids'];assert r['raw_generation']['raw_output']==g['raw_generation']['raw_output']
@pytest.mark.parametrize('fault',['contents','missing','parent','order'])
def test_replay_rejects_corrupt_initial_snapshot(tmp_path,fault):
 root=fixture(tmp_path,'timebook-add');directory=next((root/'generation_snapshots').iterdir());p=root/'model_trace.jsonl';events=[json.loads(l) for l in p.read_text().splitlines()]
 if fault=='contents':(directory/'before/README.md').write_text('Future changed data')
 if fault=='missing':(directory/'SNAPSHOT.json').unlink()
 if fault=='parent':
  x=directory/'SNAPSHOT.json';record=json.loads(x.read_text());record['input_checkpoint_id']='wrong-parent';x.write_text(json.dumps(record))
 if fault=='order':
  i=next(i for i,e in enumerate(events) if e['type']=='correction_generation_snapshot_saved');events[i],events[i+1]=events[i+1],events[i];p.write_text(''.join(json.dumps(e)+'\n' for e in events))
 with pytest.raises((ValueError,OSError)):replay(root)
