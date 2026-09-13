import json,sys,subprocess
import pytest
from pathlib import Path
from test_strong_execution_recording import execution
from rwkv_lh import task_review as review


@pytest.mark.parametrize('absolute_provider',[False,True])
def test_capture_cli_resolves_provider_path_relative_to_job_file(execution,tmp_path,absolute_provider):
    output,_,envelope=execution
    (output/'provider.jsonl').write_text(json.dumps(envelope)+'\n')
    job_dir=tmp_path/'jobs';job_dir.mkdir()
    job={'directory':'../execution','provider_trace':'../execution/provider.jsonl','task_id':'strong','arm':'takeover','repeat':1,'protocol_error_policy':'feedback','execution_identity':{k:review.digest(k) for k in review.IDENTITY_KEYS},'historical':False,'assistance':'strong_takeover'}
    if absolute_provider:job['provider_trace']=str(output/'provider.jsonl')
    (job_dir/'capture.json').write_text(json.dumps(job))
    cwd=tmp_path/'different-cwd'/'nested';cwd.mkdir(parents=True)
    script=Path(__file__).resolve().parents[1]/'scripts/review_agent_task.py'
    result=subprocess.run([sys.executable,str(script),'capture','--input',str(job_dir/'capture.json'),'--output',str(job_dir/'run.json')],cwd=cwd,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    captured=json.loads((job_dir/'run.json').read_text());assert captured['diagnostics']['input_tokens']==123 and captured['diagnostics']['output_tokens']==45
