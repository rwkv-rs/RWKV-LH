from pathlib import Path
import sys,tempfile,json,socket
sys.path.insert(0,'/home/chase/GitHub/RWKV-LH-server-teacher-r16-20260916')
from rwkv_lh.stdio_verifier import verify_python_submission
with tempfile.TemporaryDirectory(prefix='r16-stdio-check-') as d:
 w=Path(d);(w/'solution.py').write_text('import sys\nprint(sys.stdin.read().strip())\n')
 cases={'call_type':'std','fn_name':None,'inputs':['probe\n'],'outputs':['probe\n']}
 good=verify_python_submission(w,cases);assert good['passed']
 bad=verify_python_submission(w,dict(cases,outputs=['wrong\n']));assert not bad['passed'] and bad['cases'][0]['exit_code']==0
 (w/'solution.py').write_text('while True: pass\n')
 bounded=verify_python_submission(w,cases,timeout_seconds=.2);assert not bounded['passed'] and bounded['cases'][0]['termination']=='timeout'
 print(json.dumps({'hostname':socket.gethostname(),'correct_output':good,'wrong_output':bad,'bounded_execution':bounded}))
