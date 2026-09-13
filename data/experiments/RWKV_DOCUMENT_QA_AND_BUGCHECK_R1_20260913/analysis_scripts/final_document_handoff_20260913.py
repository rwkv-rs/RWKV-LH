from pathlib import Path
import json,hashlib,subprocess
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_DOCUMENT_QA_AND_BUGCHECK_R1_20260913'
p=D/'REPORT.zh-CN.md';s=p.read_text().replace('全量最终结果见 `PYTEST_FINAL_R2.log`','全量最终1594 passed、0 skipped（304.08秒），见 `PYTEST_FINAL_R2.log`');p.write_text(s)
p=R/'docs/HANDOFF.zh-CN.md';p.write_text('''# 当前进展：文档问答/代码检查入口已落地，质量门仍未达（2026-09-13）

- 产品目标仍为RWKV专属Harness/Code Agent。已新增生产只读CLI、原文材料追溯、完整独立任务进程调度和显式建议后原State续接；不强制工具顺序，不代填参数或答案。用法见 [READ_ONLY_AGENT.zh-CN.md](READ_ONLY_AGENT.zh-CN.md)。
- 任务结果：初始串行2/8合格、并发1/8；增加预算代码组1/4。后续文件权限组3/8合格、1部分、4不合格，8/8读取提交；建议组和来源标签修正组仍各3/8。全部mutation0，末三组各2次虚称实际运行验证。不是项目Strict，固定组连续两遍全合格门未达，未升级修改任务。
- RWKV能正确回答架构职责、报告缺失接口与备份不覆盖；仍会误读Writer数字、编造业务实现或已执行测试。强建议也出现误读且常未被正确利用。完整126生成输入/声明State父子关系已核验，未见观察遗漏或重复；不能推断State张量完全一致或质量根因已证实。
- rwkvrag参考已只读核对。保留原始文本、来源和回答；不移植固定多角色。服务全局锁仍串行，客户端并发不等于GPU吞吐收益。逻辑输入542391/output23038 token，strong6次/15837 token（两次建议对照复用，不重复收费计数）；未测实际费用与独占峰值资源。
- 工程修复有红绿证据：资源/启动期限、trace失败、复核旧交付隔离、完整祖先trace、建议来源标签、实际权限下唯一输入回放。最终全量1594 passed/0 skipped；原始失败、旧评分与无效夹具均保留。
- 原五个owner修改保留且排除提交；未训练、未新建数据集版本、未更新GitHub。原StateTune历史仍两轮108 optimizer steps，本轮0。
- 下一步聚焦事实忠实性和“建议/已运行”区分，先冻结证据诊断再决定纠正数据/StateTune；不继续盲加角色或预算。当前入口用于外部复核下的读取问答和代码检查，不能称无人审核稳定可用。
- [本轮报告](../data/experiments/RWKV_DOCUMENT_QA_AND_BUGCHECK_R1_20260913/REPORT.zh-CN.md)，各阶段reviews、原始EVIDENCE包与FINAL_MANIFEST同目录。复核聚合使用各阶段BATCH_LOCAL_PATHS.json（原BATCH相对路径问题保留，评分未变）。

---

'''+p.read_text())
files=[p for p in (R/'rwkv_lh').rglob('*.py') if '__pycache__' not in p.parts]
identity={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}
(D/'FINAL_SOURCE_IDENTITY.json').write_text(json.dumps(dict(files=identity,owner_changes_excluded=['rwkv_lh/controller.py','rwkv_lh/model.py','rwkv_lh/supervisor_openai.py','tests/test_hybrid_supervisor.py','tests/test_supervisor_openai.py']),indent=2)+'\n')
print('report_sha256',hashlib.sha256((D/'REPORT.zh-CN.md').read_bytes()).hexdigest())
