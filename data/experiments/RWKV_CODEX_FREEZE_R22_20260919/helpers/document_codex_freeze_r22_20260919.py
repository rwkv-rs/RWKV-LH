from pathlib import Path
import json,hashlib,shutil
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_CODEX_FREEZE_R22_20260919'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
x=json.loads((D/'RESULT.json').read_text());a=json.loads((D/'TRAINABLE_INVENTORY.json').read_text());d=json.loads((D/'TRAIN_DUPLICATE_AUDIT.json').read_text())
(D/'.gitattributes').write_text('validation/**/TASK.md -text\n')
(D/'helpers').mkdir(exist_ok=True)
for name in ['freeze_codex_increment_r22_20260919.py','audit_frozen_inventory_r22_20260919.py','document_codex_freeze_r22_20260919.py']:
 shutil.copyfile(R/'temp'/name,D/'helpers'/name)
report=f'''# R22：30条真实编码纠正正式冻结（2026-09-19）

## 任务级结果与边界

本轮没有新增Agent运行，Strict/completed/mutation及Agent终止原因均不适用。只完成已审核30条真实错误调用边界的训练准入；不把Codex写对的脚本算成RWKV独立能力。1024题纠错总任务仍未完成：延续R21的80个独立产物通过、83个已验收、941个尚未验收；旧失败、旧评分、候选和审核错误原件不变。

本轮在本地WSL运行生产验证器，不运行推理服务、不调用强模型、不训练、不push。没有修改生产代码或用户已有五处修改，没有新建data/datasets版本。

## 正式可用数据

已有v6的300条、R20的3条、本轮30条，合计333条调用边界；是三个冻结包，尚未合并成新的333行训练版本。221个来源ID、184个源内容SHA，不等于221个或333个独立项目。

|标签依据|正式行数|
|---|---:|
|真实成功读取|122|
|回答语义审核|65|
|真实仓库编辑红→绿|4|
|真实命令执行|59|
|独立程序入口写入与隔离验收|83|
|合计|333|

所有333条均由生产admit_dataset加载接受，模型、协议、tokenizer和固定回归fingerprint一致。生产collate_samples逐条核验target-only mask：输入及历史错答不作为监督目标，完整纠正目标及stop token参与监督；移位无偏差。总输入{a['input_tokens']} token、目标{a['target_tokens']} token，最长{a['max_sequence_tokens']}/24576，无截断。未执行优化器更新。

本轮新增30条均为已有Codex原样write_file目标，不生成新答案；输入283630 token、目标6485 token、最长24213/24576。素数题沿用R21已验证的早期真实边界，不补造状态或删减上下文。

## 准入证据

1. 事前REGISTRATION固定30个目标、来源、源码逐文件SHA、脚本SHA、上下文24576、3秒/测试、并发4、相似度0.9及整批失败拒绝策略。没有运行后变更门槛。
2. 原始输入通过现有生产replay_run逐token重建，核验bootstrap、观察事件唯一注入、State父子digest和全量题面可见。保留原错误输出；目标绑定原request与checkpoint。
3. R21远端证明未伪造改路径：在本地字节相同的源快照上重新运行validate_stdio_correction，生成新的本地证明。30条均原快照不通过→Harness真实写入→隔离固定私有用例通过。freeze_direct_dataset又独立复验一遍，全30通过。
4. 隐藏expected只由外部验证器持有，不进入模型输入、目标或程序工作区。私有case-only派生文件放data/test_runs/codex_freeze_r22_private，Git不收录；冻结证据引用其SHA及原acceptance SHA。无最终holdout读取。
5. 与既有303条的原边界无重复，与既有不同源内容及新增之间的UTF-8字节5-gram相似度均低于0.9。沿用生产算法和阈值，额外检查train-train；固定dev/confirmation隔离调用既有审计，不改任务或评分。此前独立评测TRAINING_EXCLUSION仅按登记文件哈希排除，无重叠。字节相似度不是语义完全独立的证明。
6. 一次来源/算法审核来自同一个Codex作者，另有隔离执行；不是两个独立语义审核，不保证所有未见边界或最坏复杂度。本轮延续既有verified_stdio证据合同，不放宽审核。

原始失败可出现在输入历史中，教模型从真实错误状态继续；只有经验证纠正进入target。这与把错误答案当正确监督有本质区别。

## 下一阶段

继续原1024题纠错主线，先将已有通过但未冻结的剩余产物补公开规格审核和真实调用绑定，再处理941个未验收任务。规格不完整、任意合法输出、数值容差和语义歧义单独隔离，不能靠固定参考字符串强造正确标签。

本轮只增加“读完题之后正确写入入口”的30个边界，仍需补“真实失败测试→定位→有效修改→复验→忠实收尾”的来源。83条stdio写入不能冒充完整Code Agent闭环覆盖；59条命令也不全是成功测试，有真实失败诊断。优先补测试反馈与诚实收尾，避免只增长算法题写入数量。

满足下一批来源质量后，再冻结一个统一候选与训练预算，沿用一轮训练方向并使用隔离、未入训的任务验证；本轮不启动训练。不按单一缺陷创建多个专用State，暂不引入RL。已有v6历史训练NO_KEEP仍有效，新增30条不是已证明的训练收益。

## 证据索引

- 增量manifest SHA-256：`{x['frozen_manifest']['sha256']}`。
- RESULT.json SHA-256：`{sha(D/'RESULT.json')}`。
- TRAINABLE_INVENTORY.json SHA-256：`{sha(D/'TRAINABLE_INVENTORY.json')}`。
- REGISTRATION.json SHA-256：`{sha(D/'REGISTRATION.json')}`。
- TRAIN_DUPLICATE_AUDIT.json SHA-256：`{sha(D/'TRAIN_DUPLICATE_AUDIT.json')}`。
- 完整工程回归结果及用户修改保持核验在FULL_TESTS.txt、FINAL_CHECKS.json；全量证据哈希在EVIDENCE_SHA256.json。旧R21报告不改写。
'''
(D/'REPORT.zh-CN.md').write_text(report)
h=R/'docs/HANDOFF.zh-CN.md';txt=h.read_text();note='''# 最新交接检查点 R22（2026-09-19）

**30条R21真实编码纠正已正式冻结并由训练加载器接受。现有可用库存333条调用边界（v6 300＋R20 3＋R22 30），仍为三个包、未创建新dataset版本；333条target-only mask全通过，最长24455/24576。新增30条生产输入/State重放、两遍本地fresh红→绿、来源去重/固定回归隔离通过；原始远端证明及错答保留。不训练、不push、生产代码未改。1024任务仍是80独立产物通过、83已验收、941未验收；本轮新增Agent运行0，非Strict或RWKV训练收益。下一步补剩余真实纠正，尤其测试反馈、有效修改与忠实收尾，不只堆算法题写入。见[R22报告](../data/experiments/RWKV_CODEX_FREEZE_R22_20260919/REPORT.zh-CN.md)及TRAINABLE_INVENTORY.json。**

'''
if not txt.startswith('# 最新交接检查点 R22'):h.write_text(note+txt)
s=R/'docs/STATETUNE_DATA_PIPELINE_STATUS.zh-CN.md';txt=s.read_text();new='''# StateTune 管线现状

## 当前结论（2026-09-19，R22）

正式冻结且训练加载器接受的库存是333条调用边界：v6 300条＋R20真实仓库诊断3条＋R22编码写入30条，分属三个包，尚未新建合并版本。构成为122读取、65回答审核、4仓库编辑、59命令、83独立程序写入；221来源ID、184内容SHA，不代表相同数量的独立项目。全333条生产target-only mask核验通过，最长24455/24576，无截断。

本轮新增30条已完成原输入/State重建、原快照失败→真实Harness写入→隔离验证通过、与既有训练来源去重及固定评测隔离。纠正目标来自Codex本人，语义审核也是同一作者，另有真实执行验证，不冒充双独立模型审核。1024题纠错尚未全部完成，80独立产物通过、83已验收、941待验收。本輪训练0、新Agent运行0，不是RWKV能力提升结论。

原v6 300条三轮和一轮训练均NO_KEEP，生产默认zero；不能只因本轮增加30条就宣称可用Code Agent已经训练完成。下一步继续来源纠正，重点补测试反馈、有效修改和忠实收尾，再冻结统一训练候选与隔离任务验收。[R22冻结证据](../data/experiments/RWKV_CODEX_FREEZE_R22_20260919/REPORT.zh-CN.md)及TRAINABLE_INVENTORY.json为当前库存依据。

以下均为历史阶段记录，数字和“当前”字样不代表最新状态。
'''
if '当前结论（2026-09-19，R22）' not in txt:s.write_text(new+txt.removeprefix('# StateTune 管线现状\n'))
print('R22 report and current-state documents written')
