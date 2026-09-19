from pathlib import Path
import sys,json,hashlib,time,concurrent.futures
B=Path('/home/chase/GitHub/RWKV-LH-teacher-1024-r17-20260916');sys.path.insert(0,str(B))
from rwkv_lh.stdio_verifier import verify_python_submission
from rwkv_lh.collection_acceptance import load_contract
from rwkv_lh.workspace_snapshot import copy_verified_workspace
from rwkv_lh.harness import ActionHarness
from rwkv_lh.schema import GoalState,TaskAction
D=Path('/home/chase/GitHub/RWKV-LH-codex-corrections-r21-20260917')
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2))
def run(row):
 folder=D/'tasks'/row['id'];candidates=sorted(folder.glob('candidate_*/solution.py'));binding=row['original_binding'];source=Path(binding['snapshot']);item=json.loads(Path(binding['conversion']).read_text());contract=load_contract(item)
 for candidate in candidates or [None]:
  tag=candidate.parent.name if candidate else 'original_recheck';dest=D/'results'/row['id']/tag
  if (dest/'RESULT.json').exists():continue
  manifest=json.loads(Path(binding['manifest']).read_text())
  for name,digest in manifest['source_files'].items():assert hashlib.sha256((Path(binding['source_root'])/name).read_bytes()).hexdigest()==digest,name
  workspace=dest/'workspace';copy_verified_workspace(source,workspace)
  assert hashlib.sha256((workspace/'TASK.md').read_bytes()).hexdigest()==row['task_sha256']
  t=time.time();baseline=verify_python_submission(workspace,contract['cases']);save(dest/'BASELINE.json',baseline)
  if candidate:
   content=candidate.read_text();author=json.loads(candidate.with_name('AUTHOR.json').read_text());assert hashlib.sha256(content.encode()).hexdigest()==author['solution_sha256'];goal=GoalState.create(request=item['job']['request'],constraints=(),workspace_root=str(workspace));obs=ActionHarness().execute(TaskAction('write_file',{'path':'solution.py','content':content}),goal).to_dict();save(dest/'WRITE_OBSERVATION.json',obs);assert obs['success'];checked=verify_python_submission(workspace,contract['cases'])
  else:checked=baseline
  record={'id':row['id'],'attempt':tag,'author':'Codex' if candidate else 'original_RWKV','baseline_passed':baseline['passed'],'passed':checked['passed'],'details':checked,'seconds':time.time()-t,'training_admitted':False,'scope':'fixed sealed private artifact cases only; semantic and complexity review separate','contract_sha256':item['acceptance_sha256']};save(dest/'RESULT.json',record);print(row['id'],tag,checked['passed'],sum(x['passed'] for x in checked['cases']),len(checked['cases']),flush=True)
rows=json.loads((D/'INVENTORY.json').read_text())['tasks'];selected=[r for r in rows if r['known_original_passed'] or list((D/'tasks'/r['id']).glob('candidate_*/solution.py'))]
save(D/'STATUS.json',{'phase':'verifying','total':1024,'selected':len(selected),'not_yet_artifact_verified':1024-len(selected)})
with concurrent.futures.ThreadPoolExecutor(4) as pool:list(pool.map(run,selected))
results=[json.loads(p.read_text()) for p in (D/'results').glob('*/*/RESULT.json')]
def summarize_results(results):
 codex=[x for x in results if x['author']=='Codex']
 final=[x for x in results if x['attempt']=='original_final_recheck']
 codex_passed={x['id'] for x in codex if x['passed']}
 original_passed={x['id'] for x in final if x['passed']}
 return {'phase':'awaiting_next_codex_authored_batch','total':1024,'overall_complete':False,
 'attempts_recorded':len(results),'unique_tasks_checked':len({x['id'] for x in results}),
 'codex_artifact_passed':len(codex_passed),'original_final_artifact_passed':len(original_passed),
 'unique_artifact_passed':len(codex_passed|original_passed),'training_admitted':0,
 'background_model_authorship':False,'scope':'offline artifact verification, not Agent Strict'}
save(D/'STATUS.json',dict(summarize_results(results),timestamp=time.time()))
