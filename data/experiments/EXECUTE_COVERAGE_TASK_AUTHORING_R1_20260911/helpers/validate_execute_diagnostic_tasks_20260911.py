from pathlib import Path
import hashlib,json,sys,shutil
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R))
from rwkv_lh.harness import ActionHarness
from rwkv_lh.schema import GoalState,TaskAction
from benchmarks.rwkv_e2e.rwkv_execute_diagnostics_v1.audit_binding import verify_with_event_binding as verify_isolated
from scripts import run_rwkv_e2e_benchmark as benchmark
O=R/'data/experiments/EXECUTE_COVERAGE_TASK_AUTHORING_R1_20260911';results=[]
for taskid in ('NEW-DIAG-01','NEW-DIAG-02'):
 f=O/taskid;task=json.loads((f/'task.json').read_text());acceptance=json.loads((f/'acceptance.json').read_text());w=O/'author_workspaces_v3'/taskid;w.mkdir(parents=True)
 for entry in task['workspace_files']:
  p=w/entry['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_text(entry['content'])
 goal=GoalState.create(request=task['user_request'],constraints=(),workspace_root=w);h=ActionHarness();events=[]
 def command(n):
  argv=['python','run_tests.py'];res=h.execute(TaskAction('run_command',{'argv':argv,'timeout':30}),goal)
  events.append({'type':'action_finished','data':{'action_id':str(n),'action':{'action_type':'run_command','arguments':{'argv':argv},'result':res.to_dict()}}});return res
 bad=command(1)
 if bad.exit_code!=1 or '1 failed, 3 passed' not in bad.output:raise SystemExit('not exactly one real failing test: '+taskid+' '+bad.output)
 module=next(p for p in w.glob('*.py') if p.name!='run_tests.py');module.write_text((f/'reference.py').read_text());good=command(2)
 if not good.success or good.exit_code!=0 or '4 passed' not in good.output:raise SystemExit('reference pytest failure: '+good.output)
 def verify(name,eventset):
  v=verify_isolated(workspace=w,acceptance=acceptance,events=eventset,observations={},private_root=O/'private_validation',timeout_seconds=90)
  r={'task_id':taskid,'variant':name,'passed':v.passed,'checks':[x.to_dict() for x in v.checks],'isolation':v.metadata};results.append(r);return v.passed
 if not verify('reference',events):raise SystemExit('reference acceptance failed: '+str(results[-1]))
 if verify('fabricated_report_without_execution',[]):raise SystemExit('fabricated evidence accepted')
 for name,content in json.loads((f/'MUTANTS.json').read_text()).items():
  module.write_text(content)
  command(len(events)+1)
  if verify(name,events):raise SystemExit('semantic mutant survived: '+name)
 module.write_text((f/'reference.py').read_text());command(3)
 (w/'tests'/next((w/'tests').glob('test_*.py')).name).write_text('def test_fake():\n    assert True\n')
 if verify('weakened_tests',events):raise SystemExit('weakened tests accepted')
 for entry in task['workspace_files']:
  if entry['path'].startswith('tests/'): (w/entry['path']).write_text(entry['content'])
 (w/'tests/conftest.py').write_text('def pytest_collection_modifyitems(items):\n    items.clear()\n')
 if verify('nested_pytest_hook',events):raise SystemExit('pytest hook accepted')
 (w/'tests/conftest.py').unlink()
 (w/'TEST_REPORT.md').write_text((w/'TEST_REPORT.md').read_text()+'forged append\n')
 if verify('tampered_report_after_real_run',events):raise SystemExit('changed report accepted')
 (f/'AUTHOR_PYTEST_OUTPUT.json').write_text(json.dumps({'initial_exit':bad.exit_code,'initial_output':bad.output,'fixed_exit':good.exit_code,'fixed_output':good.output,'sandboxed':good.metadata['sandboxed'],'role_training_source':False},ensure_ascii=False,indent=2)+'\n')
benchmark.SUITES['executediagnosticsv1']=benchmark.SuiteDefinition(key='executediagnosticsv1',title='Execute Diagnostics V1',package='benchmarks.rwkv_e2e.rwkv_execute_diagnostics_v1',tasks_schema='rwkv-execute-diagnostics-v1.tasks.v1',acceptance_schema='rwkv-execute-diagnostics-v1.acceptance.v1',expected_count=4,level_counts={'project':4})
tasks,_=benchmark.load_suite('executediagnosticsv1')
(O/'AUTHOR_VALIDATION_V3.json').write_text(json.dumps({'cases':results,'registered_suite_count':len(tasks),'all_references_passed':all(x['passed'] for x in results if x['variant']=='reference'),'all_mutants_rejected':all(not x['passed'] for x in results if x['variant']!='reference'),'author_validation_not_role_training':True},ensure_ascii=False,indent=2)+'\n');print(json.dumps({'registered':len(tasks),'variants':len(results),'references_pass':2}))
