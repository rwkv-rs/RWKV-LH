from pathlib import Path
import json,sys,hashlib
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R));from rwkv_lh import model_io
from rwkv_lh.correction_review import build_review_packet
D=R/'data/experiments/RWKV_REAL_CODING_DATA_R20_20260917'
cases=[(0,5,'loguru-stack-reproduction',"from loguru import logger\nlogger.remove()\nlogger.add(lambda message: print(str(message), end=''))\nlogger.opt(depth=1000000).info('stack-unavailable-probe')",['ValueError: call stack is not deep enough']),
(1,11,'anyio-stdin-contract',"import ast\nfrom pathlib import Path\nfound = False\nfor path in Path('src').rglob('*.py'):\n for node in ast.walk(ast.parse(path.read_text())):\n  if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == 'run_process':\n   found = True\n   args = [x.arg for x in node.args.posonlyargs + node.args.args + node.args.kwonlyargs]\n   print(str(path), 'run_process parameters:', args, flush=True)\n   assert 'stdin' in args, 'run_process lacks explicit stdin parameter'\nassert found, 'run_process definition not located'",['run_process lacks explicit stdin parameter']),
(2,7,'anyio-tempfile-exports',"import sys\nsys.path[:0] = ['src', '.deps']\nimport anyio\nnames = ['TemporaryFile', 'NamedTemporaryFile', 'SpooledTemporaryFile', 'TemporaryDirectory']\nmissing = [name for name in names if not hasattr(anyio, name)]\nprint('Missing public tempfile APIs:', missing, flush=True)\nassert not missing, 'requested temporary-file APIs unavailable'",['requested temporary-file APIs unavailable'])]
reg=[]
for n,b,ident,code,expected in cases:
 folder=D/ident;folder.mkdir(exist_ok=True);actual=json.loads((D/str(n)/f'actual{b}.json').read_text());source=json.loads((D/str(n)/'SOURCE.json').read_text())
 raw=json.dumps({'function':'run_command','params':{'argv':['python','-B','-c',code],'timeout':30,'expected_exit_code':0}},ensure_ascii=False);target=raw+model_io.JSON_CALL_STOP_SUFFIXES[0]
 packet=build_review_packet(actual_rwkv_input=actual['input_text'],candidate=raw)
 (folder/'PACKET.json').write_text(json.dumps(packet,ensure_ascii=False,indent=2));(folder/'TARGET.txt').write_text(target)
 reg.append({'id':ident,'source':source,'actual':str(D/str(n)/f'actual{b}.json'),'expected_exit_code':1,'expected_output':expected,'scope':'diagnostic next action, not implementation or task completion','author':'Codex human-authorized correction','review_required':'independent Qwen review plus Codex evidence review before real harness verification'})
(D/'REGISTRATION.json').write_text(json.dumps({'cases':reg,'gates':['source checksum and production replay','visible evidence only','two real reviewer records','real isolated command outcome','fresh second execution','current protocol token normalization','no training; no datasets version published'],'split':'train candidates; all AnyIO same repository family; no dev/holdout use'},indent=2))
