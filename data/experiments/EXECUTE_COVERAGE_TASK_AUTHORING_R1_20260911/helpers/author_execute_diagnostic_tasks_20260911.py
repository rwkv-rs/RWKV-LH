"""Author two explicitly requested development projects; no role examples or model inputs."""
from pathlib import Path
import hashlib,json
R=Path('/home/chase/GitHub/RWKV-LH');O=R/'data/experiments/EXECUTE_COVERAGE_TASK_AUTHORING_R1_20260911';B=R/'benchmarks/rwkv_e2e/rwkv_execute_diagnostics_v1';B.mkdir(exist_ok=False)
def sha(s):return hashlib.sha256(s.encode()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
helper='''from pathlib import Path
import hashlib
import subprocess
import sys

root = Path(__file__).resolve().parent
completed = subprocess.run([sys.executable, "-m", "pytest", "-q", "--color=no", "--tb=short"], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
output = completed.stdout
sources = sorted(root.glob("*.py"))
identity = "\\n".join(f"{p.name}: {hashlib.sha256(p.read_bytes()).hexdigest()}" for p in sources)
report = "# Test report\\n\\nCommand: python -m pytest -q --color=no --tb=short\\nExit code: " + str(completed.returncode) + "\\n\\n## Source identity\\n" + identity + "\\n\\n## Actual pytest output\\n```text\\n" + output + "```\\n"
(root / "TEST_REPORT.md").write_text(report, encoding="utf-8")
print(output, end="")
sys.exit(completed.returncode)
'''
projects=[
 {'id':'NEW-DIAG-01','module':'cache_policy','buggy':'def is_fresh(created_at, now, ttl):\n    """Whether a cached value can be reused at this instant."""\n    if ttl < 0 or now < created_at:\n        raise ValueError("invalid cache clock or TTL")\n    return now - created_at <= ttl\n','fixed':'def is_fresh(created_at, now, ttl):\n    """Whether a cached value can be reused at this instant."""\n    if ttl < 0 or now < created_at:\n        raise ValueError("invalid cache clock or TTL")\n    return now - created_at < ttl\n',
 'tests':'from cache_policy import is_fresh\n\ndef test_before_expiry():\n    assert is_fresh(100, 109, 10) is True\n\ndef test_after_expiry():\n    assert is_fresh(100, 111, 10) is False\n\ndef test_exact_expiry():\n    assert is_fresh(100, 110, 10) is False\n\ndef test_invalid_clock():\n    try:\n        is_fresh(100, 99, 10)\n    except ValueError:\n        return\n    assert False, "backward clock must be rejected"\n',
 'failure':'test_exact_expiry','description':'缓存策略模块已有可运行实现，但时间边界出现回归。缓存只在 age < ttl 时有效，恰好到期或超过到期必须过期；负TTL和倒退时钟必须抛ValueError。保留is_fresh(created_at, now, ttl)接口。',
 'probes':'from cache_policy import is_fresh\nfor created in (0, 13, 1000):\n    for ttl in (0, 1, 9, 300):\n        for age in (0, ttl, ttl + 1):\n            assert is_fresh(created, created + age, ttl) is (age < ttl)\nfor args in ((0,0,-1),(10,9,3)):\n    try: is_fresh(*args)\n    except ValueError: pass\n    else: raise AssertionError("invalid input accepted")\n',
 'mutants':{'always_expired':'def is_fresh(created_at, now, ttl):\n    return False\n','boundary_special_case':'def is_fresh(created_at, now, ttl):\n    if now < created_at: raise ValueError("clock")\n    return False if (created_at,now,ttl)==(100,110,10) else now-created_at <= ttl\n'}},
 {'id':'NEW-DIAG-02','module':'stock_summary','buggy':'def stock_totals(entries):\n    """Aggregate signed stock movements, retaining first-seen SKU order."""\n    totals = {}\n    for sku, quantity in entries:\n        totals[sku] = quantity\n    return list(totals.items())\n','fixed':'def stock_totals(entries):\n    """Aggregate signed stock movements, retaining first-seen SKU order."""\n    totals = {}\n    for sku, quantity in entries:\n        totals[sku] = totals.get(sku, 0) + quantity\n    return list(totals.items())\n',
 'tests':'from stock_summary import stock_totals\n\ndef test_empty():\n    assert stock_totals([]) == []\n\ndef test_single_movement():\n    assert stock_totals([("bolt", 4)]) == [("bolt", 4)]\n\ndef test_distinct_skus_keep_order():\n    assert stock_totals([("nut", 2), ("bolt", 3)]) == [("nut", 2), ("bolt", 3)]\n\ndef test_repeated_sku_accumulates():\n    assert stock_totals([("bolt", 5), ("nut", 2), ("bolt", -1)]) == [("bolt", 4), ("nut", 2)]\n',
 'failure':'test_repeated_sku_accumulates','description':'库存流水聚合已有可运行模块，重复SKU的数量出现回归。stock_totals(entries)接收(sku, signed_quantity)可迭代对象，逐SKU累加所有正负流水，并按首次出现的SKU顺序返回(sku, total)列表；零总量也必须保留，输入不可被修改。',
 'probes':'from stock_summary import stock_totals\nfor entries in ([ ("a",2),("b",7),("a",3),("b",-2)],[("x",4),("x",-4)],[("z",1),("a",2),("z",8)],[]):\n    original=list(entries)\n    expected={}\n    for sku,n in entries: expected[sku]=expected.get(sku,0)+n\n    assert stock_totals(iter(entries)) == list(expected.items())\n    assert entries == original\n',
 'mutants':{'sort_instead_of_first_seen':'def stock_totals(entries):\n    totals={}\n    for sku,q in entries: totals[sku]=totals.get(sku,0)+q\n    return sorted(totals.items())\n','drop_zero':'def stock_totals(entries):\n    totals={}\n    for sku,q in entries: totals[sku]=totals.get(sku,0)+q\n    return [(k,v) for k,v in totals.items() if v]\n'}}]
new=[];cases={}
for p in projects:
 folder=O/p['id'];folder.mkdir();testpath='tests/test_'+p['module']+'.py';source=p['module']+'.py'
 readme='# 先诊断，再修复\n\n'+p['description']+'\n\n项目已安装所需pytest，当前恰好一个测试失败。先执行 `python run_tests.py` 观察真实失败，再修复实现，最后再次执行同一命令使pytest退出0。不要修改tests、run_tests.py或添加pytest/conftest遮蔽测试；不得手写或伪造测试报告。run_tests.py调用实际pytest，原样打印输出、返回pytest退出码，并把输出和源文件SHA写入TEST_REPORT.md。初始失败是待诊断事实，不能声称测试通过。需要持久化报告的命令必须在可写的工作区运行；只读检查产生的文件不会保留。\n\n验收：实现满足上述通用规则；先失败后成功的实际命令记录；原tests和run_tests.py保持不变；TEST_REPORT.md包含实际pytest输出、Exit code: 0与当前源码SHA。不要只描述建议，提交修复后的项目和报告。\n'
 task={'task_id':p['id'],'level':'project','user_request':p['description']+' 请先运行现成的 `python run_tests.py` 诊断唯一失败，然后修复并再次运行通过，交付真实TEST_REPORT.md；完整公开合同见README.md。','capabilities':['diagnose_existing_tests','repair_regression','run_pytest','record_execution_evidence'],'workspace_files':[{'path':'README.md','content':readme},{'path':source,'content':p['buggy']},{'path':testpath,'content':p['tests']},{'path':'run_tests.py','content':helper}],'workspace_generators':[]}
 expected={testpath:sha(p['tests']),'run_tests.py':sha(helper)}
 program='''import hashlib, json, subprocess, sys
from pathlib import Path
root=Path(sys.argv[1])
EXPECTED='''+repr(expected)+'''
for path,digest in EXPECTED.items():
    assert hashlib.sha256((root/path).read_bytes()).hexdigest()==digest, "immutable test/runner changed"
assert not (root/'conftest.py').exists() and not (root/'pytest.py').exists() and not (root/'pytest').exists(), "pytest shadowing"
report=(root/'TEST_REPORT.md').read_text()
assert "Exit code: 0\\n" in report and "4 passed" in report and "FAILED" not in report, "successful actual pytest report missing"
for path in sorted(root.glob('*.py')):
    assert path.name+": "+hashlib.sha256(path.read_bytes()).hexdigest() in report, "report does not bind current source"
probe='''+repr(p['probes'])+'''
r=subprocess.run([sys.executable,'-c',probe],cwd=root,text=True,capture_output=True,timeout=15)
assert r.returncode==0, r.stdout+r.stderr
print('behavior and immutable-report checks passed')
'''
 acceptance={'runner_control':{'network_policy':'offline'},'checks':[{'kind':'project_behavior','program':program,'program_sha256':sha(program),'timeout':60,'browser':False},{'kind':'command_exit_stages','argv':['python','run_tests.py'],'stages':[p['failure']],'require_success':True}]}
 write(folder/'task.json',task);(folder/'private_verify.py').write_text(program);(folder/'reference.py').write_text(p['fixed']);write(folder/'MUTANTS.json',p['mutants']);write(folder/'acceptance.json',acceptance);new.append(task);cases[p['id']]=acceptance
old=json.loads((R/'benchmarks/rwkv_e2e/rwkv_real_project_dev_v1/tasks.json').read_text());oldcases=json.loads((R/'benchmarks/rwkv_e2e/rwkv_real_project_dev_v1/acceptance.json').read_text())['cases']
controls=[next(t for t in old['tasks'] if t['task_id']==k) for k in ('RP-CLI-01','RP-WEB-02')]
for t in controls:cases[t['task_id']]=oldcases[t['task_id']]
write(B/'tasks.json',{'schema_version':'rwkv-execute-diagnostics-v1.tasks.v1','tasks':controls+new});write(B/'acceptance.json',{'schema_version':'rwkv-execute-diagnostics-v1.acceptance.v1','cases':cases});(B/'__init__.py').write_text('"""Owner-authorized diagnose-first development tasks and unchanged controls."""\n')
write(O/'AUTHORING_REGISTRATION.json',{'authorization':'Owner2026-09-11 explicitly delegates finalization ofNEW-DIAG-01/02 and acceptance; no role data or training created by authoring','source_kind':'owner-authorized authored development benchmark, not collected real-user requests','new_ids':[p['id'] for p in projects],'controls_unchanged':[t['task_id'] for t in controls],'primary_uses_existing_harness_success_semantics':True,'actual_and_expected_exit_codes_reported_separately':True,'final_acceptance_requires_real_pytest_exit_zero':True,'role_training_samples':0,'author_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
print(json.dumps({'new_tasks':len(new),'controls':len(controls),'package':str(B)}))
