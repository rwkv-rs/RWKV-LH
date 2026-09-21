"""One registered calendar CLI run followed by isolated project acceptance."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[1]

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--base-url',required=True)
    args=parser.parse_args();root=args.root.resolve()
    registration=json.loads((root/'CALENDAR_REGISTRATION.json').read_text())
    task=root/'calendar-source/TASK.md'
    verifier=ROOT/'benchmarks/calendar_project_v1/verify.py'
    if sha(task)!=registration['task_sha256'] or sha(verifier)!=registration['verifier_sha256']:
        raise ValueError('registered task or verifier changed')
    if (root/'agent-run').exists() or (root/'TRIAL_RESULT.json').exists():
        raise ValueError('one run only: output already exists')
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for _ in range(90):
        try:
            with opener.open(args.base_url+'/models',timeout=2) as response:
                models=json.load(response)
            if registration['model'] in {m['id'] for m in models['data']}:break
        except Exception:pass
        time.sleep(1)
    else:raise RuntimeError('registered model did not become available')
    (root/'MODELS_PREFLIGHT.json').write_text(json.dumps(models,indent=2)+'\n')
    environment=dict(os.environ)
    values={'BASE_URL':args.base_url,'MODEL':registration['model'],'MODEL_SHA256':registration['model_sha256'],
        'BACKEND_PROFILE':'vllm-rwkv-native','MAX_MODEL_LEN':str(registration['context_tokens']),
        'ACTION_MAX_OUTPUT_TOKENS':str(registration['output_tokens']),'STATE_TRANSPORT':'native_required',
        'STATE_PROFILE_ID':'zero','STATE_PROFILE_SHA256':'0'*64,'STATE_PROFILE_DELIVERY':'request',
        'TOOL_DISCLOSURE_MODE':'full','DEFAULT_TEMPERATURE':'0.1','DEFAULT_TOP_P':'1.0','DEFAULT_TOP_K':'0',
        'PROXY_URL':'','API_KEY':''}
    environment.update({'RWKV_LH_EXECUTOR_'+k:v for k,v in values.items()})
    command=[sys.executable,'-m','scripts.run_rwkv_agent','--source-workspace',str(task.parent),
        '--output-dir',str(root/'agent-run'),'--task-id',registration['task_id'],
        '--request',task.read_text(),'--base-url',args.base_url,'--model',registration['model'],
        '--model-sha256',registration['model_sha256'],'--max-calls',str(registration['max_calls']),
        '--max-seconds',str(registration['max_seconds']),'--record-generation-snapshots']
    started=time.time()
    with (root/'AGENT_CLI.log').open('w') as log:
        process=subprocess.run(command,cwd=ROOT,env=environment,stdout=log,stderr=log)
    if sha(task)!=registration['task_sha256'] or sha(verifier)!=registration['verifier_sha256']:
        raise ValueError('task or verifier changed during run')
    purpose_path=root/'agent-run/execution/SOURCE_PURPOSE.json'
    if purpose_path.parent.is_dir():
        purpose_path.write_text(json.dumps({'source_purpose':'development_evaluation',
            'registration_sha256':sha(root/'CALENDAR_REGISTRATION.json')},indent=2)+'\n')
    workspace=root/'agent-run/workspace'
    with (root/'ACCEPTANCE.log').open('w') as log:
        verdict=subprocess.run([sys.executable,str(ROOT/'scripts/test_calendar_project.py'),
            '--workspace',str(workspace),'--output',str(root/'calendar-acceptance')],cwd=ROOT,
            stdout=log,stderr=log)
    result={'agent_exit_code':process.returncode,'acceptance_exit_code':verdict.returncode,
        'elapsed_seconds':time.time()-started,'repeat_count':1,'training_started':False,
        'source_purpose':'development_evaluation_not_training'}
    (root/'TRIAL_RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result));return verdict.returncode

if __name__=='__main__':raise SystemExit(main())
