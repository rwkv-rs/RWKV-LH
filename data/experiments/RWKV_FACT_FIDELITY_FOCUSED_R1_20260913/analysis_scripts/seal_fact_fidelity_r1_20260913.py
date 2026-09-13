from pathlib import Path
import json,hashlib,tarfile,shutil,subprocess
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_FACT_FIDELITY_FOCUSED_R1_20260913'
p=R/'docs/HANDOFF.zh-CN.md';p.write_text('''# 当前进展：事实忠实性聚焦诊断完成，GitHub更新已获授权（2026-09-13）

- 已按owner最新指示推送当前开发分支至3e57e3e3并核验远端；不合并main，原五个owner修改仍未提交。无条件local-only推送钩子仅对获准命令覆盖，长期设置保留。
- 继续聚焦数字身份/比较关系及建议测试/真实执行。两题各两遍：任务合格1/4、部分满足1/4、不合格2/4，提交4/4、mutation0、已提交答案虚假运行声明0；不是项目Strict或普遍稳定。
- 数字原值及对象两遍正确；一遍额外生成相同百分比之间的错误“提升”关系。代码两遍将测试标为未运行，但仍把需求当实现或误报健康检查；不能将0虚假运行声明当作整题修好。
- 11生成/30602输入/3672输出token，6读取，1截断拒绝及1反馈消费后提交；所有返回输入/观察/声明State父子关系核验。无生产改动，与上轮1594 passed/0 skipped源码逐文件一致，本轮不重复相同全测。
- 新问题聚焦只为定位，不作为提示修复收益；未提供真实HTTP已执行的阳性观察，不能推断完整来源区分。无强模型、新数据集或训练。
- 下一步仍围绕这两个错误：数字看原值+对象+关系；代码优先预注册单独代码/联合需求的来源混淆定位，再纳入真实执行观察。不得程序代填或预判State根因。
- [报告](../data/experiments/RWKV_FACT_FIDELITY_FOCUSED_R1_20260913/REPORT.zh-CN.md)，冻结、逐项外部review、真实证据包及SHA同目录；原实验不重算。

---

'''+p.read_text())
A=D/'analysis_scripts';A.mkdir(exist_ok=True)
for p in (R/'temp').glob('*fact_fidelity*20260913.py'):
 s=p.read_text()
 if p.name=='audit_fact_fidelity_r1_20260913.py':s=s.replace('sys.path.insert(0,str(R))','sys.path.insert(0,str(D/"source"))')
 (A/p.name).write_text(s)
with tarfile.open(D/'EVIDENCE.tar.gz','w:gz') as tar:
 for root in ['runs','source']:
  for p in sorted((D/root).rglob('*')):
   if p.is_file() and '__pycache__' not in p.parts:tar.add(p,arcname=str(p.relative_to(D)),recursive=False)
files=[]
for p in sorted(D.rglob('*')):
 if not p.is_file() or p.relative_to(D).parts[0] in ('runs','source') or p.name=='MANIFEST.json':continue
 files.append(dict(path=str(p.relative_to(D)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
(D/'MANIFEST.json').write_text(json.dumps(dict(files=files),ensure_ascii=False,indent=2)+'\n')
paths=[str((D/f['path']).relative_to(R)) for f in files]+[str((D/'MANIFEST.json').relative_to(R)),'docs/HANDOFF.zh-CN.md']
subprocess.run(['git','add','-f','--',*paths],cwd=R,check=True)
print('report sha256',hashlib.sha256((D/'REPORT.zh-CN.md').read_bytes()).hexdigest())
