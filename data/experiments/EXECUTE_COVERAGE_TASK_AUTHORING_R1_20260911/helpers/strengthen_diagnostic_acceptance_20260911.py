from pathlib import Path
import json,hashlib
R=Path('/home/chase/GitHub/RWKV-LH');O=R/'data/experiments/EXECUTE_COVERAGE_TASK_AUTHORING_R1_20260911';B=R/'benchmarks/rwkv_e2e/rwkv_execute_diagnostics_v1'
def sha(s):return hashlib.sha256(s.encode()).hexdigest()
def write(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n')
tasks=json.loads((B/'tasks.json').read_text());acceptance=json.loads((B/'acceptance.json').read_text())
for task in tasks['tasks']:
 if not task['task_id'].startswith('NEW-DIAG-'):continue
 f=O/task['task_id'];module=next(x for x in task['workspace_files'] if x['path'].endswith('.py') and '/' not in x['path'] and x['path']!='run_tests.py');helper=next(x for x in task['workspace_files'] if x['path']=='run_tests.py');oldhelper=sha(helper['content']);helper['content']=helper['content'].replace('print(output, end="")','print(report, end="")')
 program=(f/'private_verify.py').read_text().replace(oldhelper,sha(helper['content']))
 allowed=[x['path'] for x in task['workspace_files']]+['TEST_REPORT.md']
 marker='''\nBOUND_EVENTS = None  # trusted-event-binding-v1
assert BOUND_EVENTS is not None, "missing trusted runtime events"
ALLOWED = '''+repr(allowed)+'''
for path in root.rglob('*'):
    if not path.is_file(): continue
    rel=path.relative_to(root)
    if any(part in ('.pytest_cache','__pycache__') for part in rel.parts): continue
    assert rel.as_posix() in ALLOWED, "unexpected file/test/config: "+str(rel)
commands=[]
for event in BOUND_EVENTS:
    action=(event.get('data') or {}).get('action') or {}
    if action.get('action_type') not in ('check_command','run_command'): continue
    if action.get('arguments',{}).get('argv') != ['python','run_tests.py']: continue
    commands.append(action.get('result') or {})
source_name='''+repr(module['path'])+'''
initial_sha='''+repr(sha(module['content']))+'''
failure_seen=False
matched=False
for result in commands:
    output=result.get('output','')
    if result.get('exit_code')==1 and '1 failed, 3 passed' in output and source_name+': '+initial_sha in output:
        failure_seen=True
    if failure_seen and result.get('success') is True and result.get('exit_code')==0 and output==report:
        matched=True
assert matched, "report is not exact successful command stdout after the real seeded failure"
'''
 program=program.replace("probe=",marker+'\nprobe=',1)
 if task['task_id']=='NEW-DIAG-02':
  # The private probe string is a repr literal, so extend it as a second probe.
  program=program.replace("r=subprocess.run", "probe += '\\nentries=[(\\\"b\\\",2),(\\\"a\\\",3),(\\\"b\\\",-2)]\\noriginal=list(entries)\\nassert stock_totals(entries)==[(\\\"b\\\",0),(\\\"a\\\",3)]\\nassert entries==original\\n'\nr=subprocess.run")
 compile(program,str(f/'private_verify.py'),'exec')
 (f/'private_verify.py').write_text(program);write(f/'task.json',task)
 case={'runner_control':{'network_policy':'offline'},'checks':[{'kind':'project_behavior','program':program,'program_sha256':sha(program),'timeout':60,'browser':False}]}
 write(f/'acceptance.json',case);acceptance['cases'][task['task_id']]=case
write(B/'tasks.json',tasks);write(B/'acceptance.json',acceptance)
