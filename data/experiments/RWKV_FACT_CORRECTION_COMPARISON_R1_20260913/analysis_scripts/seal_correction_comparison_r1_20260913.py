from pathlib import Path
import json,hashlib,tarfile,subprocess
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_FACT_CORRECTION_COMPARISON_R1_20260913'
p=R/'docs/HANDOFF.zh-CN.md';p.write_text('''# 当前进展：三类纠正比较已完成，只有需求归属候选两遍合格（2026-09-13）

- 6次提交，任务合格2、部分满足2、不合格2，mutation/非法调用/虚假已运行0；均strong_advised，不是RWKV独立收益或项目Strict。
- 数字关系第一遍修掉旧错但吸收换算禁令，第二遍仍保留旧错；需求误当实现两遍核心纠正合格但有轻微瑕疵；状态码两遍保留404，一遍传播到验证预期。不能宣称跨顺序稳定。
- 每候选一次strong建议、同父State＋同建议隔离续接两遍，三份父结果不重算。strong也有误评：多加等价百分比禁令、忽略原答案已有读取说明。独立记录建议正确性、实际采用与任务质量。
- 6新RWKV/32444输入/3074输出token；strong3调用/8778总token。8次父历史调用单列去重。完整输入/观察/建议及State父子关系核验；实际费用未知，不声称成本收益。
- 无生产代码变化，与1594 passed/0 skipped源码一致；无新数据集或训练，原owner修改保留。完整比较到此结束，不继续堆一般建议追分。
- 下一步只将经过验证的局部纠正与强建议错误/RWKV未采用分开做数据覆盖审查；整篇回答仍有瑕疵，均未标训练合格。不因一类两遍合格就升级写任务或直接训练。
- [报告](../data/experiments/RWKV_FACT_CORRECTION_COMPARISON_R1_20260913/REPORT.zh-CN.md)，原始strong/RWKV证据、原契约逐项review及SHA同目录。

---

'''+p.read_text())
A=D/'analysis_scripts';A.mkdir(exist_ok=True)
for p in (R/'temp').glob('*correction*20260913.py'):
 if 'RWKV_FACT_CORRECTION_COMPARISON_R1_20260913' not in p.read_text():continue
 s=p.read_text()
 if p.name.startswith('audit_'):s=s.replace('sys.path.insert(0,str(R))','sys.path.insert(0,str(D/"source"))')
 (A/p.name).write_text(s)
with tarfile.open(D/'EVIDENCE.tar.gz','w:gz') as tar:
 for root in ['runs','source','advice']:
  for p in sorted((D/root).rglob('*')):
   if p.is_file() and '__pycache__' not in p.parts:tar.add(p,arcname=str(p.relative_to(D)),recursive=False)
files=[]
for p in sorted(D.rglob('*')):
 if not p.is_file():continue
 rel=str(p.relative_to(D))
 if any(rel.startswith(x+'/') for x in ['runs','source','advice']) or rel=='MANIFEST.json':continue
 files.append(dict(path=rel,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
(D/'MANIFEST.json').write_text(json.dumps(dict(files=files),ensure_ascii=False,indent=2)+'\n')
paths=[str((D/f['path']).relative_to(R)) for f in files]+[str((D/'MANIFEST.json').relative_to(R)),'docs/HANDOFF.zh-CN.md'];subprocess.run(['git','add','-f','--',*paths],cwd=R,check=True)
print('report SHA',hashlib.sha256((D/'REPORT.zh-CN.md').read_bytes()).hexdigest())
