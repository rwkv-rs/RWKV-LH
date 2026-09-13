from pathlib import Path
import json,re,sys
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R))
from rwkv_lh import task_review as r
D=R/'data/experiments/RWKV_FEEDBACK_TASK_BASELINE_R1_20260913';name=sys.argv[1]
audit=json.loads((D/name).read_text());rows=[]
for run in audit['runs']:
 for call in run['calls']:
  path=D/'runs'/run['run']/'actual_inputs'/f'{call["request"]}.txt';text=path.read_text()
  matches=list(re.finditer(r'Assistant: ```json\n\s*\nUser: Function output:',text))
  rows.append({'run':run['run'],'request':call['request'],'input_sha256':r.file_digest(path),'unclosed_empty_assistant_prefixes_before_user':len(matches),'examples':[text[max(0,m.start()-35):m.end()+180] for m in matches[:2]],'output_tokens':call['output_tokens'],'finish_reason':call['finish']})
r.write_once(D/('BOUNDARIES_'+name),{'scope':'literal exact input structure; not proof of measured behavioral effect','definition':'assistant JSON opener directly followed by a new User event without a body or closing fence; distinct from final intended generation prefix','rows':rows,'mechanism':'candidate rollback restores generation-ready input checkpoint; append renders a new user event and assistant opener without retiring the prior pending opener','source_locations':['rwkv_lh/model_io.py:401','rwkv_lh/model_session.py:1204','rwkv_lh/model.py:2982'],'next_test':'failed candidate versus committed response; repeated errors; multiple pending events; both native State and prompt replay. No unconditional repair by event type, since some rejection notices follow committed outputs.'})
print('inputs checked',len(rows),'affected',sum(v['unclosed_empty_assistant_prefixes_before_user']>0 for v in rows))
