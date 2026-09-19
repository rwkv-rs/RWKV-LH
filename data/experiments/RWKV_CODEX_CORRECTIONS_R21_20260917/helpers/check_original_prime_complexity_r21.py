from pathlib import Path
import sys,json,subprocess,time
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R));from rwkv_lh.model_io import parse_model_command
D=R/'data/experiments/RWKV_CODEX_CORRECTIONS_R21_20260917';folder=D/'tasks/CODING-10b4dce37b1ded8286ed1f0c';raw=json.loads((D/'EARLY_PRIME_BOUNDARIES.json').read_text())[0]['output'];command=parse_model_command(raw);code=command.arguments['content'];original=folder/'original_decoded_prime.py';original.write_text(code);compile(code,'original','exec');record={'basis':'Public sample and stated maximum N, no private expected outputs','original_command_parsed':True,'original_python_compiles':True,'runs':[]}
for name,p in [('original',original),('corrected',folder/'candidate_01/solution.py')]:
 for n in [10,100000000]:
  start=time.monotonic()
  try:r=subprocess.run(['python3',str(p)],input=f'{n}\n',text=True,capture_output=True,timeout=3);x={'version':name,'n':n,'exit':r.returncode,'stdout':r.stdout,'timeout':False}
  except subprocess.TimeoutExpired:x={'version':name,'n':n,'timeout':True}
  x['seconds']=time.monotonic()-start;record['runs'].append(x)
assert all(x.get('stdout')=='4\n' for x in record['runs'] if x['n']==10)
assert next(x for x in record['runs'] if x['n']==100000000 and x['version']=='original')['timeout']
assert not next(x for x in record['runs'] if x['n']==100000000 and x['version']=='corrected')['timeout']
(folder/'ORIGINAL_COMPLEXITY_DIAGNOSIS.json').write_text(json.dumps(record,indent=2));print(record)
