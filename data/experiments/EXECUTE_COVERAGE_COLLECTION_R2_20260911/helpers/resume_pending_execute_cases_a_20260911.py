from pathlib import Path
import json,hashlib,subprocess
R=Path('/home/chase/GitHub/RWKV-LH');O=R/'data/experiments/EXECUTE_COVERAGE_COLLECTION_R2_20260911'
failed=O/'PRE_GENERATION_LOCATION_PREFLIGHT';failed.mkdir(exist_ok=False)
for t in ['NEW-DIAG-01','NEW-DIAG-02']:
 assert not (O/f'all_zero/cases/{t}').exists()
 for suffix in ['log','completion.json']:(O/f'{t}.{suffix}').rename(failed/f'{t}.{suffix}')
(O/'COMPLETION.json').rename(failed/'COMPLETION.json')
(failed/'EXPLANATION.json').write_text(json.dumps({'cause':'Isolated default plan_cache_dir differed from frozen absolute path; exact config guard rejected before case_started or any model call.','fixed':'Set existing SUPERVISOR_PLAN_CACHE_DIR to original frozen path; public settings now identical. No schema, prompts, model parameters or task change.','model_requests':0,'model_reruns':0,'continuation_within_original_7200_seconds':True},indent=2)+'\n')
s=(R/'temp/continue_execute_coverage_a_isolated_20260911.py').read_text();a=s.index('# First two workers');b=s.index('started=datetime.fromisoformat',a)
s=s[:a]+"records=[json.loads((O/f'{t}.completion.json').read_text()) for t in ['RP-CLI-01','RP-WEB-02']]\n"+s[b:]
p=R/'temp/run_pending_execute_cases_a_20260911.py';p.write_text(s)
subprocess.run([str(R/'.venv/bin/python'),str(p)],cwd=R,check=True)
