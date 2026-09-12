from pathlib import Path
import json,hashlib,shutil
R=Path('/home/chase/GitHub/RWKV-LH');old=R/'data/experiments/RWKV_READ_PARAMETER_DESCRIPTION_R3_20260912';D=R/'data/experiments/RWKV_READ_PARAMETER_DESCRIPTION_R4_20260912';D.mkdir(exist_ok=False)
shutil.copytree(old/'frozen_before',D/'frozen_before',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
for name in ['SOURCE_BEFORE.json','PREEXISTING_CHANGES.json']:shutil.copyfile(old/name,D/name)
fixtures=[]
for name in ['full_code-1-r1','missing-2-r1']:
 p=old/'after/runs'/name/'model_trace.jsonl';es=[json.loads(l) for l in p.read_text().splitlines()];g=next(e['raw_generation'] for e in es if e['type']=='model_session_generation_returned')
 fixtures.append({'source':str(p.parent.relative_to(R)),'trace_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'raw_output':g['raw_output']})
(R/'tests/fixtures/read_file_parameter_failures_r4.json').write_text(json.dumps(fixtures,ensure_ascii=False,indent=2)+'\n')
p=R/'tests/test_read_file_parameter_contract.py';s=p.read_text();s=s.replace("\n\n\n@pytest.mark.parametrize", "\nFAILURES += json.loads(\n    (Path(__file__).parent / 'fixtures/read_file_parameter_failures_r4.json').read_text()\n)\n\n\n@pytest.mark.parametrize",1)
s=s.replace("ids=['end-byte-first', 'end-byte-second', 'byte-line-limits']","ids=['end-byte-first', 'end-byte-second', 'byte-line-limits', 'code-regression', 'missing-regression']")
s=s.replace("assert 'end_byte is output metadata only' in definition['description']", "assert 'caller supplies no ending position' in definition['description']\n    assert 'end_byte' not in definition['description']")
s=s.replace("assert 'end_byte is output metadata only' in client.prompts[0]", "assert 'caller supplies no ending position' in client.prompts[0]")
p.write_text(s)
for stem in ['run_read_description_comparison','analyze_read_description_comparison','bundle_read_description_sources']:
 text=(R/f'temp/{stem}_r3_20260912.py').read_text().replace('RWKV_READ_PARAMETER_DESCRIPTION_R3_20260912','RWKV_READ_PARAMETER_DESCRIPTION_R4_20260912')
 if stem=='run_read_description_comparison':
  text=text.replace("'description_only_ast_verified':True,", "'description_only_ast_verified':True,'predecessor':'R3 NO_KEEP: primary 19/21 to 14/21, supplement 3/3 to 2/3; archived independently','hypothesis':'Concise positive legal-input semantics without naming illegal fields or negative sentinel examples; no causal claim about negative priming yet','additional_trials':'Only this additional description candidate; no further automatic wording search this task',")
 (R/f'temp/{stem}_r4_20260912.py').write_text(text)
print('R4 prepared; original baseline retained')
