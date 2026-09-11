"""Upload frozen manifests and source, verify all bytes, activate existing units."""
from pathlib import Path
import json
import shutil
import subprocess
ROOT = Path('/home/chase/GitHub/RWKV-LH-full-trace-r2-20260911')
OUT = Path('/home/chase/GitHub/RWKV-LH/data/experiments/FULL_TRACE_DEPLOYMENT_R2_20260911')
REMOTE = Path('/home/chase/GitHub/RWKV-LH-full-trace-runtime-r2-20260911')
if '1502 passed' not in (OUT / 'PYTEST.log').read_text():
    raise SystemExit('Current full regression has not passed')
if subprocess.check_output(['git', 'diff', 'de029c88', '--', 'rwkv_lh', 'scripts', 'pyproject.toml', 'uv.lock'], cwd=ROOT):
    raise SystemExit('Production source differs from user-authorized commit')
REMOTE.mkdir(exist_ok=False)
shutil.copytree(OUT / 'deployment_source/source', REMOTE / 'source')
(REMOTE / 'validation').mkdir()
for name in ('PROJECT_SOURCE.json', 'ENGINE_SOURCE.json', 'DECODER_MANIFEST.json'):
    shutil.copyfile(OUT / name, REMOTE / 'validation' / name)
previous = subprocess.run(['ssh', '-o', 'BatchMode=yes', 'rwkv-8222', 'systemctl', '--user', 'cat',
                          'rwkv-lh-native-current.service', 'rwkv-lh-selector-current.service'], capture_output=True, check=True)
(OUT / 'PREVIOUS_UNITS.txt').write_bytes(previous.stdout)
subprocess.run(['ssh', 'rwkv-8222', 'mkdir', '-p', str(REMOTE / 'source'), str(REMOTE / 'engine'), str(REMOTE / 'validation')], check=True)
subprocess.run(['rsync', '-a', str(REMOTE / 'source') + '/', 'rwkv-8222:' + str(REMOTE / 'source') + '/'], check=True)
subprocess.run(['rsync', '-a', str(ROOT / 'temp/native_engine_role_chain_r1_20260910') + '/', 'rwkv-8222:' + str(REMOTE / 'engine') + '/'], check=True)
names = ('PROJECT_SOURCE.json', 'ENGINE_SOURCE.json', 'DECODER_MANIFEST.json', 'launch_native.sh', 'launch_selector.sh')
subprocess.run(['rsync', '-a', *(str(OUT / name) for name in names), 'rwkv-8222:' + str(REMOTE / 'validation') + '/'], check=True)
verification = (OUT / 'launch_native.sh').read_text().split('\nexec ', 1)[0] + '\n'
result = subprocess.run(['ssh', 'rwkv-8222', 'bash', '-s'], input=verification, text=True, capture_output=True)
(OUT / 'UPLOADED_SOURCE_VERIFICATION.log').write_text(result.stdout + result.stderr)
if result.returncode:
    raise SystemExit(result.returncode)
subprocess.run(['rsync', '-a', str(OUT / 'rwkv-lh-native-current.service'), str(OUT / 'rwkv-lh-selector-current.service'),
                'rwkv-8222:/home/chase/.config/systemd/user/'], check=True)
subprocess.run(['ssh', 'rwkv-8222', 'systemctl', '--user', 'daemon-reload'], check=True)
subprocess.run(['ssh', 'rwkv-8222', 'systemctl', '--user', 'restart', 'rwkv-lh-native-current.service', 'rwkv-lh-selector-current.service'], check=True)
(OUT / 'ACTIVATION.json').write_text(json.dumps({'source_verified_before_activation': True, 'server_git_executed': False,
    'remote_root': str(REMOTE), 'fresh_state_store': True, 'health_validation': 'pending',
    'model_files_unchanged': True, 'production_commit': 'de029c88'}, indent=2) + '\n')
print('Frozen source uploaded and verified; both current services restarted; health pending.', flush=True)
