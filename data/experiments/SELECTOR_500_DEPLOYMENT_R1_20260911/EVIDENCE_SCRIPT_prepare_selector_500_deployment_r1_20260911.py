from pathlib import Path
import subprocess,shutil
R=Path('/home/chase/GitHub/RWKV-LH')
W=Path('/home/chase/GitHub/RWKV-LH-selector-500-r1-20260911')
O=R/'data/experiments/SELECTOR_500_DEPLOYMENT_R1_20260911'
O.mkdir(exist_ok=False)
for old,new in [('freeze_execute_coverage_deployment_a_20260911.py','freeze_selector_500_deployment_r1_20260911.py'),
                ('upload_execute_coverage_deployment_a_20260911.py','upload_selector_500_deployment_r1_20260911.py')]:
    s=(R/'temp'/old).read_text()
    s=s.replace("ROOT = Path('/home/chase/GitHub/RWKV-LH')",f"ROOT = Path({str(W)!r})")
    s=s.replace("OUT = ROOT / 'data/experiments/EXECUTE_COVERAGE_DEPLOYMENT_A_20260911'",f"OUT = Path({str(O)!r})")
    s=s.replace('RWKV-LH-execute-coverage-a-20260911','RWKV-LH-selector-500-runtime-r1-20260911')
    s=s.replace('c6b46d01','3ae1efcc').replace('1464 passed','1479 passed')
    (R/'temp'/new).write_text(s)
shutil.copyfile(R/'data/experiments/STATETUNE_EFFECTIVE_FREEZE_R3_20260911/PYTEST_FINAL.log',O/'PYTEST.log')
assert not subprocess.check_output(['git','diff','5edcccde','3ae1efcc','--','rwkv_lh','scripts','tests','pyproject.toml','uv.lock'],cwd=R)
for name in ['freeze_selector_500_deployment_r1_20260911.py','upload_selector_500_deployment_r1_20260911.py']:
    subprocess.run([str(R/'.venv/bin/python'),str(R/'temp'/name)],cwd=W,check=True)
