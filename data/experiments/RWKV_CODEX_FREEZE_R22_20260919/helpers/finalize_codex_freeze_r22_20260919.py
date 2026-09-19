from pathlib import Path
import json,hashlib,subprocess,re,shutil
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_CODEX_FREEZE_R22_20260919'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
log=R/'data/test_runs/r22_full_pytest_20260919.log';text=log.read_text();match=re.search(r'(\d+) passed in ([\d.]+)s',text);assert match and int(match[1])==1894 and not re.search(r'\d+ (failed|skipped|errors?)',text)
assert subprocess.check_output(['git','diff','--cached','--name-only'],cwd=R,text=True).strip()==''
reg=json.loads((D/'REGISTRATION.json').read_text());actual={str(p.relative_to(R)):sha(p) for folder in ('rwkv_lh','scripts','tests') for p in sorted((R/folder).rglob('*.py'))};assert actual==reg['source_identity']
owner=['rwkv_lh/controller.py','rwkv_lh/model.py','rwkv_lh/supervisor_openai.py','tests/test_hybrid_supervisor.py','tests/test_supervisor_openai.py']
shutil.copyfile(log,D/'FULL_TESTS.txt')
shutil.copyfile(Path(__file__),D/'helpers'/Path(__file__).name)
proofs=json.loads((D/'frozen_increment/stdio_validation.json').read_text())['rows'];assert len(proofs)==30 and all(not r['validation']['baseline']['passed'] and r['validation']['after']['passed'] for r in proofs)
checks={'pytest':{'passed':int(match[1]),'skipped':0,'seconds':float(match[2]),'log_sha256':sha(log),'command':'CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES=0 .venv/bin/python -m pytest -q tests/'},'production_source_unchanged':True,'owner_file_sha256':{p:sha(R/p) for p in owner},'fresh_frozen_validation':{'boundaries':len(proofs),'passed_cases':sum(len(r['validation']['after']['cases']) for r in proofs)},'model_calls':0,'optimizer_steps':0,'datasets_version_created':False,'github_updated':False}
(D/'FINAL_CHECKS.json').write_text(json.dumps(checks,indent=2)+'\n')
report=D/'REPORT.zh-CN.md';t=report.read_text();t+=f'\n完整工程回归：{match[1]} passed、0 skipped（{match[2]}秒），与登记生产源码逐文件SHA一致；用户五处修改保持原字节。最终冻结复验30/30来源、1055/1055固定测试用例通过。新增与旧来源最近字节5-gram余弦0.55556，低于0.9。只证明固定标签准入，不是新Agent验收。\n';report.write_text(t)
checks['report_sha256']=sha(report)
(D/'FINAL_CHECKS.json').write_text(json.dumps(checks,indent=2)+'\n')
manifest={str(p.relative_to(D)):sha(p) for p in sorted(D.rglob('*')) if p.is_file() and p.name!='EVIDENCE_SHA256.json'}
(D/'EVIDENCE_SHA256.json').write_text(json.dumps(manifest,indent=2)+'\n')
paths=[str(D.relative_to(R)),'docs/HANDOFF.zh-CN.md','docs/STATETUNE_DATA_PIPELINE_STATUS.zh-CN.md']
subprocess.run(['git','add','--',*paths],cwd=R,check=True)
staged=subprocess.check_output(['git','diff','--cached','--name-only','-z'],cwd=R).decode().split('\0');staged=[p for p in staged if p]
assert not set(staged)&set(owner)
for p in staged:
 assert p.startswith(str(D.relative_to(R))+'/') or p in paths[1:]
 data=subprocess.check_output(['git','show',':'+p],cwd=R)
 assert data==(R/p).read_bytes(),f'Git changes raw bytes: {p}'
# Source TASK.md and snapshots retain original whitespace byte-for-byte.
subprocess.run(['git','diff','--cached','--check','--','docs',str(D.relative_to(R)/'helpers')],cwd=R,check=True)
print(json.dumps({'staged_files':len(staged),'tests':checks['pytest'],'report_sha256':sha(report),'source_bytes_preserved':True},indent=2))
