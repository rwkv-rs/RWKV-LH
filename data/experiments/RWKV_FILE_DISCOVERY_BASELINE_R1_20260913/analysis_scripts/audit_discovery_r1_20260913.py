from pathlib import Path
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_FILE_DISCOVERY_BASELINE_R1_20260913'
s=(R/'temp/audit_direct_candidate_tasks_r2_20260913.py').read_text().replace("P=R/'data/experiments/RWKV_LIMIT_AND_STATETUNE_CAMPAIGN_R1_20260913';D=P/'evaluation_r2';sys.path.insert(0,str(P/'training_runtime/source_r2'))","P=R/'data/experiments/RWKV_FILE_DISCOVERY_BASELINE_R1_20260913';D=P;sys.path.insert(0,str(P/'source'))")
s=s.replace("key=sha_text('candidate-task-r2:'", "key=sha_text('discovery-r1:'")
s=s.replace("'final':r['final']}","'final':r['final'],'observations':[__import__('json').loads(q.read_text()) for q in sorted(p.glob('observation_*.json'))]}")
# Reuse previously sealed exact-input and State ancestry audit; complete-read remains diagnostic, not task gate.
exec(compile(s,str(R/'temp/audit_direct_candidate_tasks_r2_20260913.py'),'exec'),{})
