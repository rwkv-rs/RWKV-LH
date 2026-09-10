"""Register a fresh fixed-budget command-path collection, separate from token-budget experiment."""
from pathlib import Path
import hashlib
import json
import subprocess
ROOT = Path('/home/chase/GitHub/RWKV-LH')
OUT = ROOT / 'data/experiments/COMMAND_PATH_COLLECTION_R1_20260910'
OUT.mkdir(exist_ok=False)
source = (ROOT / 'temp/run_execution_revalidation_r2_20260910.py').read_text()
source = source.replace('EXECUTION_EVIDENCE_REVALIDATION_R2_20260910', OUT.name)
source = source.replace("('RP-CLI-02', 'RP-DATA-01', 'RP-DATA-02', 'RP-FULL-01', 'RP-FULL-02', 'RP-WEB-01', 'RP-WEB-02')",
                        "('RP-CLI-01', 'RP-FULL-02', 'RP-WEB-01', 'RP-WEB-02')")
source = source.replace('12600', '7200')
source = source.replace("'Strict / 12', 'completed / 12'", "'Strict / 4', 'completed / 4'")
start = source.index("        'owner_authorization':")
end = source.index("        'source_kind':", start)
source = source[:start] + "        'owner_authorization': '2026-09-10 owner explicitly authorized deployment of21c0cf45 and a fresh official collection ofRP-WEB-02 and similar command-check tasks; no new training dataset version is created by collection',\n        'purpose': 'Observe command execution coverage through the unchanged production Agent at Executor1800; do not force tool choices or mix the separate budget experiment',\n" + source[end:]
source = source.replace('"""Collect the seven explicitly authorized balance-recovery development tasks through the production runner.',
                        '"""Collect four explicitly authorized command-path development tasks through the production runner.')
driver = ROOT / 'temp/run_command_path_collection_r1_20260910.py'
with driver.open('x') as stream:
    stream.write(source)
registration = {'round_id': OUT.name, 'task_ids': ['RP-CLI-01', 'RP-FULL-02', 'RP-WEB-01', 'RP-WEB-02'],
    'selection_basis': 'Existing authorized CLI, full-stack, and Web development tasks require public command/browser checks; includes original excluded WEB02. No hidden scoring implementation read.',
    'production_commit': '21c0cf45', 'executor_max_output_tokens': 1800,
    'task_concurrency': 1, 'per_case_wall_seconds': 1800, 'total_wall_seconds': 7200,
    'max_transitions': 200, 'native_transport_resume_attempts': 1,
    'keep_metric': 'No ability KEEP claim from collection alone; count actual check/run actions and validated Selector execute coverage.',
    'no_forced_commands': True, 'no_budget_treatment': True, 'optimizer_steps': 0,
    'driver_sha256': hashlib.sha256(driver.read_bytes()).hexdigest(),
    'deployment_manifest_sha256': hashlib.sha256((ROOT / 'data/experiments/AUDIT_FANOUT_DEPLOYMENT_R1_20260910/PROJECT_SOURCE.json').read_bytes()).hexdigest()}
(OUT / 'COMMAND_COLLECTION_PREREGISTRATION.json').write_text(json.dumps(registration, ensure_ascii=False, indent=2) + '\n')
subprocess.run([str(ROOT / '.venv/bin/python'), str(driver), 'prepare'], cwd=ROOT, check=True)
