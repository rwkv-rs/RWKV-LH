from pathlib import Path
import sys,json,re
R=Path('/home/chase/GitHub/RWKV-LH');sys.path[:0]=[str(R),str(R/'tests')]
from test_unified_controller import build,call
D=R/'data/experiments/RWKV_FEEDBACK_TASK_BASELINE_R1_20260913';root=D/'boundary_reproduction';root.mkdir(exist_ok=False)
controller,store,workspace,client,model=build(root,[call('read_file',path='sample.txt',max_lines=10),call('final_answer',text='mock terminal')])
(workspace/'sample.txt').write_text('fixture only')
controller.run('RUN')
pattern=r'Assistant: ```json\n\s*\nUser: Function output:'
text=client.prompts[1]
(D/'BOUNDARY_REPRODUCTION.json').write_text(json.dumps({'mock_only':True,'feedback_input':text,'unclosed_boundary_found':bool(re.search(pattern,text))},ensure_ascii=False,indent=2)+'\n')
assert re.search(pattern,text) is None,'new user observation follows an unclosed, empty assistant JSON prefix after candidate rollback'
