from pathlib import Path
import json,hashlib
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_DISCOVERY_INPUT_MENU_R1_20260913';r=json.loads((D/'dev/smoke-readonly-r2/RESULT.json').read_text())
review={'smoke-readonly-r2':{'answer_sha256':hashlib.sha256(r['final'].encode()).hexdigest(),'location':1,'answer':2,'fidelity':2,'task_pass':True,'false_work_completion':False,'quality':'基本满足，说明简略','note':'定位verify_public.py，说明/health健康检查和不认证booking行为的主要边界；原README与脚本都实际读取。未列JSON ok断言，记录为说明不完整；冻结规则要求有用回答而非锚点逐字逐条全覆盖，不把这句话解读为显式否认响应体检查，没有编造已执行验证。','reviewer':'Codex source-based external review; arm identity known from progress, not claimed blind'}}
(D/'SUBMITTED_ANSWER_REVIEW.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n')
s=(R/'temp/score_input_menu_r1_20260913.py').read_text();s=s.replace("assert all(p['final'] is None for p in packets),'Submitted answers require separate source-based review.'","labels=json.loads((D/'SUBMITTED_ANSWER_REVIEW.json').read_text())")
needle="for m in mechanical.values():"
insert="""for v in reviews:
 if v['run'] not in labels:continue
 p=next(p for p in packets if mapping[p['id']]==v['run']);label=labels[v['run']];assert hashlib.sha256(p['final'].encode()).hexdigest()==label['answer_sha256'];v.update(label)
for p in packets:
 if p['final'] is not None:assert mapping[p['id']] in labels,'Unreviewed final'
"""
s=s.replace(needle,insert+needle,1)
s=s.replace("tasks=len(ms),task_pass=0,submitted=0", "tasks=len(ms),task_pass=sum(v['task_pass'] for v in reviews if v['arm']==a),submitted=sum(m['submitted'] for m in ms)")
s=s.replace("No task success benefit from reducing displayed menu alone; does not rule out schema wording, layout or observation packaging effects; no production retention, no training", "Neither arm meets two repetitions each4/4 with zero illegal parameters; one useful submission is insufficient for fixed-group stability or broad causal attribution; no production retention or training")
(R/'temp/score_input_menu_final_r1_20260913.py').write_text(s)
