"""Freeze current project and canonical engine locally; never run Git remotely."""
from pathlib import Path
import hashlib
import json
import shutil
import shlex
import subprocess
import sys

ROOT = Path('/home/chase/GitHub/RWKV-LH-selector-500-r1-20260911')
sys.path.insert(0, str(ROOT))
from rwkv_lh.inference.uploaded_sources import ENGINE_SCHEMA, PROJECT_SCHEMA, source_inventory
from rwkv_lh.exact_tool_selector.native_network_service import NATIVE_SELECTOR_DECODER_MANIFEST_SCHEMA
from rwkv_lh.exact_tool_selector.native_network_protocol import NATIVE_SELECTOR_DECODER_ID, NATIVE_SELECTOR_DECODER_PROTOCOL
from rwkv_lh.exact_tool_selector.input_protocol import CURRENT_G1J_NETWORK_SELECTOR_INPUT_PROTOCOL
from rwkv_lh.exact_tool_selector.network_protocol import NETWORK_EXACT_TOOL_LABELS
from rwkv_lh.goal_state_protocols import selector_intent_v6

OUT = Path('/home/chase/GitHub/RWKV-LH/data/experiments/SELECTOR_500_DEPLOYMENT_R1_20260911')
BUNDLE = OUT / 'deployment_source'
REMOTE = Path('/home/chase/GitHub/RWKV-LH-selector-500-runtime-r1-20260911')
ENGINE = ROOT / 'temp/native_engine_role_chain_r1_20260910'
PYTHON = '/home/chase/GitHub/RWKV-LH/data/runtime/engines/vllm-rwkv-67f0c5996c50/.venv/bin/python'
REVISION = json.loads((ROOT / 'data/experiments/ROLE_CHAIN_ROOT_REPAIR_R1_20260910/ENGINE_BEFORE.json').read_text())['engine_revision']

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(path, value):
    with path.open('x') as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    return sha(path)

def records(path):
    return [{'path': name, 'sha256': checksum, 'bytes': size}
            for name, (checksum, size) in sorted(source_inventory(path).items())]

BUNDLE.mkdir(exist_ok=False)
source = BUNDLE / 'source'
source.mkdir()
for folder in ('rwkv_lh', 'scripts'):
    shutil.copytree(ROOT / folder, source / folder,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo'))
for name in ('pyproject.toml', 'uv.lock'):
    shutil.copyfile(ROOT / name, source / name)
project_records = records(source)
engine_records = records(ENGINE)
assert len(engine_records) == 6393
project_sha = write(OUT / 'PROJECT_SOURCE.json', {
    'schema_version': PROJECT_SCHEMA, 'project_root': str(REMOTE / 'source'),
    'source_root': '.', 'files': project_records})
engine_sha = write(OUT / 'ENGINE_SOURCE.json', {
    'schema_version': ENGINE_SCHEMA, 'engine_root': str(REMOTE / 'engine'),
    'engine_revision': REVISION, 'source_root': '.', 'files': engine_records})
decoder_sha = write(OUT / 'DECODER_MANIFEST.json', {
    'schema_version': NATIVE_SELECTOR_DECODER_MANIFEST_SCHEMA, 'decoder_id': NATIVE_SELECTOR_DECODER_ID,
    'decoder_protocol': NATIVE_SELECTOR_DECODER_PROTOCOL, 'input_protocol': CURRENT_G1J_NETWORK_SELECTOR_INPUT_PROTOCOL,
    'target_prefix': selector_intent_v6.TARGET_PREFIX, 'labels': list(NETWORK_EXACT_TOOL_LABELS),
    'algorithm': 'eligible_token_sequence_trie_vocab_logit_argmax', 'token_tie_break': 'lowest_token_id',
    'state_policy': 'fresh_initial_state_per_evaluation', 'menu_aggregation': 'majority_then_registered_class_order',
    'downstream_decoder_trained': False, 'generated_text': False})
common = {'PYTHONPATH': f'{REMOTE / "source"}:{REMOTE / "engine"}', 'PYTHONDONTWRITEBYTECODE': '1',
          'OMP_NUM_THREADS': '4', 'VLLM_RWKV7_WKV_MODE': 'fp32io16',
          'RWKV_NATIVE_ENGINE_SOURCE_MANIFEST': str(REMOTE / 'validation/ENGINE_SOURCE.json'),
          'RWKV_NATIVE_ENGINE_SOURCE_MANIFEST_SHA256': engine_sha,
          'RWKV_NATIVE_PROJECT_SOURCE_MANIFEST': str(REMOTE / 'validation/PROJECT_SOURCE.json'),
          'RWKV_NATIVE_PROJECT_SOURCE_MANIFEST_SHA256': project_sha}
native_env = {**common, 'CUDA_VISIBLE_DEVICES': 'GPU-1faf7f09-25f4-2515-b707-6e0766aa841d',
    'VLLM_PLUGINS': 'rwkv_lh_native_state', 'VLLM_USE_V2_MODEL_RUNNER': '1',
    'VLLM_RWKV7_NATIVE_STATE_ENABLED': '1', 'VLLM_RWKV7_NATIVE_STATE_CACHE_CAPACITY': '8',
    'VLLM_RWKV7_NATIVE_STATE_STORE_CAPACITY': '0',
    'VLLM_RWKV7_NATIVE_STATE_DIR': str(REMOTE / 'state/blobs'),
    'RWKV_NATIVE_REQUEST_JOURNAL': str(REMOTE / 'state/journal.sqlite3')}
selector_env = {**common, 'CUDA_VISIBLE_DEVICES': 'GPU-5d61943c-0955-e221-92a8-318915f5a3a0'}
verify = [PYTHON, '-B', '-c', 'import vllm; from rwkv_lh.inference.native_source_identity import verify_native_source_identity; print(verify_native_source_identity(engine_file=vllm.__file__))']
native_cmd = [PYTHON, '-B', '-m', 'vllm.entrypoints.cli.main', 'serve',
    '/home/chase/GitHub/RWKV-LH/data/models/rwkv7-g1j-13.3b-vllm-v1',
    '--host', '127.0.0.1', '--port', '18234', '--tokenizer-mode', 'rwkv',
    '--trust-request-chat-template', '--enable-auto-tool-choice', '--tool-call-parser', 'rwkv',
    '--max-model-len', '16384', '--served-model-name', 'rwkv7-g1j-13.3b-zero-state-capability-ctx16384',
    '--gpu-memory-utilization', '0.35', '--max-num-batched-tokens', '32768', '--max-num-seqs', '16',
    '--override-generation-config', '{"temperature":0.1}']
selector_cmd = [PYTHON, '-B', '-m', 'rwkv_lh.exact_tool_selector.native_network_service',
    '--engine-root', str(REMOTE / 'engine'), '--engine-revision', REVISION, '--engine-python', PYTHON,
    '--engine-source-manifest', str(REMOTE / 'validation/ENGINE_SOURCE.json'),
    '--engine-source-manifest-sha256', engine_sha,
    '--model-artifact', '/home/chase/GitHub/RWKV-LH-selector-r1-20260909/model',
    '--model-name', 'rwkv7-g1j-2.9b-20260831-ctx16384',
    '--model-sha256', '1f920b94c4684e8463f36d8b71df23a8b50551f7776d39eec9ec6970471d460b',
    '--decoder-manifest', str(REMOTE / 'validation/DECODER_MANIFEST.json'), '--decoder-sha256', decoder_sha,
    '--context-tokens', '16384', '--runtime-temp', str(REMOTE / 'selector_runtime'), '--port', '29621']
for name, env, cmd in (('native', native_env, native_cmd), ('selector', selector_env, selector_cmd)):
    launcher = '#!/bin/bash\nset -euo pipefail\n' + ''.join(f'export {k}={shlex.quote(v)}\n' for k,v in env.items())
    launcher += shlex.join(verify) + '\nexec ' + shlex.join(cmd) + '\n'
    (OUT / f'launch_{name}.sh').write_text(launcher)
    unit = f'[Unit]\nDescription=RWKV-LH current {name}\n[Service]\nType=simple\nWorkingDirectory={REMOTE / "source"}\nExecStart=/bin/bash {REMOTE / "validation" / ("launch_" + name + ".sh")}\nRestart=no\nTimeoutStopSec=30\n[Install]\nWantedBy=default.target\n'
    (OUT / f'rwkv-lh-{name}-current.service').write_text(unit)
write(OUT / 'DEPLOYMENT_FREEZE.json', {
    'round_id': OUT.name, 'local_parent_commit': subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip(),
    'working_tree_changes': False, 'freeze_script_sha256': sha(Path(__file__)),
    'project_manifest_sha256': project_sha, 'project_files': len(project_records),
    'engine_manifest_sha256': engine_sha, 'engine_files': len(engine_records),
    'decoder_sha256': decoder_sha, 'remote_root': str(REMOTE), 'server_git_executed': False,
    'fresh_state_store_required': True, 'optimizer_steps': 0})
print(json.dumps({'project_sha256': project_sha, 'project_files': len(project_records),
                  'engine_sha256': engine_sha, 'decoder_sha256': decoder_sha}))
