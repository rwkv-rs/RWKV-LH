"""Prepare one common driver and an ordered launcher for the preregistered two arms."""
from pathlib import Path
import hashlib
import json
ROOT = Path('/home/chase/GitHub/RWKV-LH')
OUT = ROOT / 'data/experiments/EXECUTOR_OUTPUT_BUDGET_R1_20260910'
source = (ROOT / 'temp/run_command_path_collection_r1_20260910.py').read_text()
source = source.replace("ROUND = ROOT / 'data/experiments/COMMAND_PATH_COLLECTION_R1_20260910'", "ARM = os.environ['RWKV_LH_EXPERIMENT_ARM']\nARM_BUDGETS = {'baseline1800': 1800, 'candidate3600': 3600}\nif ARM not in ARM_BUDGETS:\n    raise SystemExit('Unknown preregistered arm')\nEXECUTOR_TOKENS = ARM_BUDGETS[ARM]\nROUND = ROOT / 'data/experiments' / ('EXECUTOR_OUTPUT_BUDGET_' + ARM.upper() + '_R1_20260910')")
source = source.replace("('RP-CLI-01', 'RP-FULL-02', 'RP-WEB-01', 'RP-WEB-02')", "('RP-FULL-02', 'RP-WEB-02')")
source = source.replace('7200', '3600').replace("'Strict / 4', 'completed / 4'", "'Strict / 2', 'completed / 2'")
source = source.replace("'case_concurrency': 1, 'max_transitions_per_case': 200,", "'case_concurrency': 1, 'max_transitions_per_case': 200, 'executor_max_output_tokens': EXECUTOR_TOKENS,")
source = source.replace("    return benchmark, roles, planner, selector", """    from functools import wraps
    original_next_command = benchmark.LongHorizonModel.next_command
    @wraps(original_next_command)
    def with_registered_budget(self, *args, **kwargs):
        if kwargs.get('max_output_tokens', 1800) != 1800:
            raise ValueError('Unexpected caller output budget')
        kwargs['max_output_tokens'] = EXECUTOR_TOKENS
        return original_next_command(self, *args, **kwargs)
    benchmark.LongHorizonModel.next_command = with_registered_budget
    return benchmark, roles, planner, selector""")
start = source.index("        'owner_authorization':")
end = source.index("        'source_kind':", start)
source = source[:start] + "        'owner_authorization': '2026-09-10 owner explicitly authorized separate preregistered Executor output budget experiment',\n        'purpose': 'Fresh same-code two-arm budget pilot; only next_command max_output_tokens differs, no rescoring',\n" + source[end:]
driver = ROOT / 'temp/run_executor_output_budget_r1_20260910.py'
with driver.open('x') as stream:
    stream.write(source)
binding = {'driver_path': str(driver), 'driver_sha256': hashlib.sha256(driver.read_bytes()).hexdigest(),
           'preregistration_sha256': hashlib.sha256((OUT / 'PREREGISTRATION.json').read_bytes()).hexdigest(),
           'source_files_modified': False, 'runtime_argument_override': 'LongHorizonModel.next_command max_output_tokens',
           'arms': ['baseline1800', 'candidate3600'], 'collection_prerequisite': 'COMMAND_PATH_COLLECTION_R1_20260910/COMPLETION.json'}
(OUT / 'DRIVER_BINDING.json').write_text(json.dumps(binding, indent=2) + '\n')
print(json.dumps(binding))
