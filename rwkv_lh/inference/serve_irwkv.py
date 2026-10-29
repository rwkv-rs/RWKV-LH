"""Prepare or launch one pinned irwkv Executor with persistent State plugins."""
import argparse
import json
import os
from pathlib import Path
import subprocess

from rwkv_lh.skyrl_training import gpu_uuid, sealed, sha
from rwkv_lh.gpu_resources import require_idle_gpu
from .uploaded_sources import ENGINE_SCHEMA, PROJECT_SCHEMA, verify_manifest
from .irwkv_artifact import verify_artifact, verify_vocabulary
from rwkv_lh.token_budget import VOCAB_PATH

SCHEMA = 'rwkv-lh.irwkv-deployment.v1'
LOCK = json.loads(Path(__file__).with_name('irwkv.lock.json').read_text())


def launch_configuration(registration, output):
    if registration.get('schema_version') != SCHEMA:
        raise ValueError('current irwkv deployment registration is required')
    if registration.get('protocol') != 'executor':
        raise ValueError('current Executor protocol is required; retired protocols cannot be deployed')
    device = gpu_uuid(registration['gpu_index'])
    if registration['gpu_uuid'] != device:
        raise ValueError('registered GPU identity differs')
    context, port = registration['context_tokens'], registration['port']
    memory = registration['gpu_memory_utilization']
    eager = registration.get('enforce_eager', True)
    if type(eager) is not bool:
        raise ValueError('enforce_eager must be an explicit boolean')
    tuning = registration.get('flashrwkv_tuning_mode', 'tune')
    if tuning not in ('inspect', 'require', 'tune'):
        raise ValueError('invalid FlashRWKV2 tuning mode')
    if (type(context) is not int or context <= 0 or type(port) is not int or not 0 < port < 65536
            or type(memory) not in (int, float) or not 0 < memory < 1):
        raise ValueError('invalid context, port or explicit GPU memory fraction')
    plugins = ['rwkv_lh_state_worker', 'rwkv_lh_native']
    output = Path(output).absolute()
    env = dict(CUDA_VISIBLE_DEVICES=device, IRWKV_PLUGINS=','.join(plugins),
        IRWKV_USE_V2_MODEL_RUNNER='1', IRWKV_USE_RUST_FRONTEND='0',
        IRWKV_RWKV_TUNING_MODE=tuning,
        IRWKV_RWKV7_NATIVE_STATE_DIR=str(output/'state_tensors'),
        IRWKV_RWKV7_NATIVE_STATE_STORE_CAPACITY='0', IRWKV_RWKV7_NATIVE_STATE_CACHE_CAPACITY='8',
        RWKV_NATIVE_REQUEST_JOURNAL=str(output/'journal.sqlite3'))
    for scope, key in (('ENGINE','engine_source'), ('PROJECT','project_source')):
        env['RWKV_NATIVE_'+scope+'_SOURCE_MANIFEST'] = registration[key]['path']
        env['RWKV_NATIVE_'+scope+'_SOURCE_MANIFEST_SHA256'] = registration[key]['sha256']
    from rwkv_lh.runtime.structured_output import DECODER_BACKEND
    argv = [str(registration['python']), '-m', 'rwkv_lh.inference.native_server', 'serve',
        registration['model_root'], '--served-model-name', registration['model_name'],
        '--host', '127.0.0.1', '--port', str(port), '--dtype', 'bfloat16',
        '--generation-config', 'irwkv',
        '--enable-scale-out',
        '--middleware', 'rwkv_lh.inference.sampling_policy.reject_unsupported_sampling',
        '--mamba-ssm-cache-dtype', 'float32', '--mamba-cache-mode', 'none',
        '--tensor-parallel-size', '1', '--pipeline-parallel-size', '1',
        '--max-model-len', str(context), '--max-num-seqs', '1',
        '--gpu-memory-utilization', str(memory), '--enable-chunked-prefill',
        '--no-enable-prefix-caching',
        '--worker-extension-cls', 'rwkv_lh.inference.irwkv_plugin.NativeStateWorkerExtension',
        '--structured-outputs-config', json.dumps({'backend': DECODER_BACKEND})]
    if eager:
        argv.append('--enforce-eager')
    return dict(command=argv, environment=env, training_started=False, optimizer_steps=0)


def prepare(registration, output):
    prepared = launch_configuration(registration, output)
    for key, schema in (('engine_source', ENGINE_SCHEMA), ('project_source', PROJECT_SCHEMA)):
        ref=registration[key]
        verified=verify_manifest(Path(ref['path']), ref['sha256'], expected_schema=schema,
            expected_revision=LOCK['revision'] if key == 'engine_source' else None)
        prepared[key]=verified
    model=verify_artifact(registration['model_root'], expected_manifest=registration['model_manifest'])
    verify_vocabulary(registration['model_root'], VOCAB_PATH)
    prepared['model_manifest_sha256']=registration['model_manifest']['sha256']
    if model['source_vocabulary_sha256'] != sha(VOCAB_PATH):
        raise ValueError('model vocabulary source differs')
    output=Path(output).absolute()
    output.mkdir(parents=True, exist_ok=False)
    (output/'PREPARED.json').write_text(json.dumps(prepared,indent=2)+'\n')
    return prepared


def run(registration, output):
    prepared=prepare(registration,output)
    actual=subprocess.check_output(['nvidia-smi','--query-gpu=uuid','--format=csv,noheader',
        '-i',str(registration['gpu_index'])],text=True).strip()
    if actual != registration['gpu_uuid']:
        raise ValueError('physical GPU UUID differs; no inference started')
    snapshot = require_idle_gpu(actual)
    (Path(output) / 'GPU_START.json').write_text(json.dumps(snapshot, indent=2) + '\n')
    env=dict(os.environ, **prepared['environment'])
    env.pop('PYTHONPATH',None)
    with (Path(output)/'irwkv.log').open('xb') as log:
        # Third-party JIT builds inspect cwd for pyproject.toml. The frozen
        # engine source is not a build context and has no VCS metadata.
        process=subprocess.run(prepared['command'],cwd=str(Path(output).absolute()),env=env,
            stdout=log,stderr=subprocess.STDOUT,check=False)
    result=dict(exit_code=process.returncode,log_sha256=sha(Path(output)/'irwkv.log'))
    (Path(output)/'EXIT.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registration',required=True)
    parser.add_argument('--registration-sha256',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    registration=sealed(dict(path=args.registration,sha256=args.registration_sha256))
    result=(run if args.execute else prepare)(registration,args.output)
    print(json.dumps(result,indent=2))
    return int(result.get('exit_code',0)!=0)


if __name__=='__main__':raise SystemExit(main())
