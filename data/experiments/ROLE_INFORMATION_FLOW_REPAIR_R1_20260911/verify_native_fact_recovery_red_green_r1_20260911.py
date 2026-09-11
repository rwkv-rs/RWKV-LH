"""Compare the same recovery regression against the frozen method in memory."""
from pathlib import Path
import ast, hashlib, json, subprocess, sys, tempfile
ROOT=Path('/home/chase/GitHub/RWKV-LH')
sys.path.insert(0,str(ROOT/'tests'))
import test_role_information_flow as regression
import rwkv_lh.model as model_module
cls=model_module.LongHorizonModel
current=cls._rebuild_native_executor_cache
source=subprocess.check_output(['git','show','2a54bf46:rwkv_lh/model.py'],cwd=ROOT,text=True)
node=next(n for c in ast.parse(source).body if isinstance(c,ast.ClassDef) and c.name=='LongHorizonModel' for n in c.body if isinstance(n,ast.FunctionDef) and n.name=='_rebuild_native_executor_cache')
module=ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[]))
namespace=dict(vars(model_module))
exec(compile(module,'frozen-native-recovery-method','exec'),namespace)
cls._rebuild_native_executor_cache=namespace['_rebuild_native_executor_cache']
cls._EXECUTOR_CAUSAL_FACT_LIMITS=(12,8,4,2,0)
base=ROOT/'data/test_runs/role_recovery_history'
base.mkdir(parents=True,exist_ok=True)
try:
    with tempfile.TemporaryDirectory(dir=base) as directory:
        regression.test_native_cache_rebuild_keeps_early_required_facts(Path(directory))
except AssertionError:
    red='failed_as_expected_early_facts_missing'
else:
    raise AssertionError('Frozen recovery unexpectedly passed')
finally:
    cls._rebuild_native_executor_cache=current
    del cls._EXECUTOR_CAUSAL_FACT_LIMITS
with tempfile.TemporaryDirectory(dir=base) as directory:
    regression.test_native_cache_rebuild_keeps_early_required_facts(Path(directory))
print(json.dumps(dict(baseline='2a54bf46',source_sha256=hashlib.sha256(source.encode()).hexdigest(),red=red,green='passed',old_module_written_to_disk=False),indent=2))
