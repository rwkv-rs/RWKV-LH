from pathlib import Path
import json,hashlib,tarfile,subprocess
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_SOURCE_ATTRIBUTION_CONTROL_R1_20260913'
p=R/'docs/HANDOFF.zh-CN.md';p.write_text('''# 当前进展：来源归属对读取顺序敏感，进入针对性纠正准备（2026-09-13）

- 六次任务提交6/6，完全合格0、部分满足3、不合格3；mutation/协议错误/虚假已运行声明均0。不是项目Strict，不把部分正确与编造等同。
- 源码单独两遍均正确判断业务缺失与db未使用，但有附加host推断错误或工具记录遗漏；先源码后README两遍都把需求当实现；反转文件列表后RWKV自主先README后源码，两遍恢复主要实现有无判断，仍残留404/501等错误。顺序效应仅限当前固定来源，不证明State数值损坏，也不能硬编码源码最后读。
- 与前轮数字原值正确但比较关系失真一起，当前目标为事实与来源/关系对应。已准备三份唯一advice构造器的真实候选输入，无隐藏答案，尚未调用强模型、生成纠正或训练；详见本轮NEXT_STEP。
- 16返回/42115输入/3922输出token，10读取，全输入/观察/声明State父子关系及workspace SHA核验。生产源码未改，与1594 passed/0 skipped源码一致，不重复相同全测。无新数据集或训练，原owner修改保留。
- [报告](../data/experiments/RWKV_SOURCE_ATTRIBUTION_CONTROL_R1_20260913/REPORT.zh-CN.md)，冻结、逐项评分、证据包与SHA同目录。下一步纠正必须跨两种顺序验证，不能靠程序选事实、补答案或增加固定角色掩盖问题。

---

'''+p.read_text())
A=D/'analysis_scripts';A.mkdir(exist_ok=True)
for pattern in ['*source_attribution*20260913.py','*source_order*20260913.py','prepare_source_correction_candidates_r1_20260913.py']:
 for p in (R/'temp').glob(pattern):
  s=p.read_text()
  if p.name.startswith('audit_source_'):
   source='../source' if 'order' in p.name else 'source';s=s.replace('sys.path.insert(0,str(R))',f'sys.path.insert(0,str(D/"{source}"))')
  (A/p.name).write_text(s)
with tarfile.open(D/'EVIDENCE.tar.gz','w:gz') as tar:
 for root in ['runs','source','order_probe/runs']:
  for p in sorted((D/root).rglob('*')):
   if p.is_file() and '__pycache__' not in p.parts:tar.add(p,arcname=str(p.relative_to(D)),recursive=False)
files=[]
for p in sorted(D.rglob('*')):
 if not p.is_file():continue
 rel=str(p.relative_to(D))
 if any(rel.startswith(x+'/') for x in ['runs','source','order_probe/runs']) or rel=='MANIFEST.json':continue
 files.append(dict(path=rel,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
(D/'MANIFEST.json').write_text(json.dumps(dict(files=files),ensure_ascii=False,indent=2)+'\n')
paths=[str((D/f['path']).relative_to(R)) for f in files]+[str((D/'MANIFEST.json').relative_to(R)),'docs/HANDOFF.zh-CN.md']
subprocess.run(['git','add','-f','--',*paths],cwd=R,check=True)
print('report SHA',hashlib.sha256((D/'REPORT.zh-CN.md').read_bytes()).hexdigest())
