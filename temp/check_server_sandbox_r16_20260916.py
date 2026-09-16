from pathlib import Path
import sys,subprocess,json,tempfile,socket
R=Path('/home/chase/GitHub/RWKV-LH-server-teacher-r16-20260916');sys.path.insert(0,str(R))
from rwkv_lh.harness import ActionHarness
from rwkv_lh.schema import GoalState
with tempfile.TemporaryDirectory(prefix='r16-isolation-') as d:
 w=Path(d)/'workspace';w.mkdir();secret=Path(d)/'private';secret.write_text('not visible')
 goal=GoalState.create(request='Engineering sandbox check',workspace_root=str(w),constraints=[])
 code="from pathlib import Path; import sys; assert not Path(sys.argv[1]).exists(); print(sys.stdin.read(),end=''); Path('written.txt').write_text('ok')"
 argv,path=ActionHarness()._bubblewrap_command(goal,w,[sys.executable,'-c',code,str(secret)])
 p=subprocess.run(argv,input='actual-server-stdin\n',text=True,capture_output=True,timeout=20,env={'PATH':path,'LANG':'C.UTF-8'})
 result={'hostname':socket.gethostname(),'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'workspace_write':(w/'written.txt').is_file(),'private_file_visible':False if p.returncode==0 else 'unknown'}
 print(json.dumps(result));assert p.returncode==0 and p.stdout=='actual-server-stdin\n' and result['workspace_write']
