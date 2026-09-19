from pathlib import Path
import ast,json
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_CODEX_CORRECTIONS_R21_20260917';p=R/'temp/verify_codex_corrections_r21.py';s=p.read_text();old=s[s.index("save(D/'STATUS.json',{'phase':'awaiting_next_codex_authored_batch'"):]
function='''def summarize_results(results):
 codex=[x for x in results if x['author']=='Codex']
 final=[x for x in results if x['attempt']=='original_final_recheck']
 codex_passed={x['id'] for x in codex if x['passed']}
 original_passed={x['id'] for x in final if x['passed']}
 return {'phase':'awaiting_next_codex_authored_batch','total':1024,'overall_complete':False,
 'attempts_recorded':len(results),'unique_tasks_checked':len({x['id'] for x in results}),
 'codex_artifact_passed':len(codex_passed),'original_final_artifact_passed':len(original_passed),
 'unique_artifact_passed':len(codex_passed|original_passed),'training_admitted':0,
 'background_model_authorship':False,'scope':'offline artifact verification, not Agent Strict'}
'''
fixture=[{'id':'a','author':'Codex','attempt':'candidate_01','passed':True},{'id':'a','author':'Codex','attempt':'candidate_02','passed':True},{'id':'b','author':'original_RWKV','attempt':'original_recheck','passed':True},{'id':'b','author':'original_RWKV','attempt':'original_final_recheck','passed':True},{'id':'c','author':'original_RWKV','attempt':'original_recheck','passed':True},{'id':'c','author':'original_RWKV','attempt':'original_final_recheck','passed':False}]
namespace={};exec(function,namespace);after=namespace['summarize_results'](fixture);before={'codex':sum(x['passed'] and x['author']=='Codex' for x in fixture),'original':sum(x['passed'] and x['author']=='original_RWKV' for x in fixture)};assert before=={'codex':2,'original':3};assert after['codex_artifact_passed']==1 and after['original_final_artifact_passed']==1 and after['unique_artifact_passed']==2
s=s[:s.index(old)]+function+"save(D/'STATUS.json',dict(summarize_results(results),timestamp=time.time()))\n";s=s.replace("'not_yet_reviewed':1024-len(selected)","'not_yet_artifact_verified':1024-len(selected)");p.write_text(s);(D/'upload'/p.name).write_text(s);(D/'PROGRESS_COUNTING_REGRESSION.json').write_text(json.dumps({'scope':'Temporary batch status aggregator, not private scoring changes','fixture':fixture,'before_duplicate_counts':before,'after':after},indent=2));print('counter regression red -> green')
