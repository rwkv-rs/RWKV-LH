# 纠正候选与用量审计

这是生产trace的离线工程入口，不调用模型、不生成数据集或启动训练，不进入Controller决策。新增候选验证针对已经记录的单次write_file/replace_text边界；复杂修改、测试命令纠正和回答标签仍各自审核，不能假设一个检查器覆盖所有能力。

## 调用

在WSL中，仅使用GPU 0：

```bash
CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES=0 .venv/bin/python scripts/audit_rwkv_evidence.py usage --run /absolute/existing/task
CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES=0 .venv/bin/python scripts/audit_rwkv_evidence.py correction --registration /absolute/frozen-registration.json
```

usage输出JSON到stdout。correction成功验证返回0；验证不通过返回1并保留VALIDATION.json，准入前身份/参数错误抛异常，原始registration必须随调用日志保留。新输出目录必须不存在且与来源不重叠；不得使用data/datasets目录来绕过数据版本授权。调用前先冻结registration，执行后不得换评分或命令重算同轮收益。

## 候选登记字段

|字段|内容|
|---|---|
|run_root、checkpoint_id、model_sha256|真实生产执行目录、要纠正的生成checkpoint及模型SHA|
|source_files|相对路径→SHA映射，至少包含RESULT、state_snapshot、model_trace，存在时包含PARENT_TRACE，并冻结全部tool_snapshots/*/call.json|
|snapshot、snapshot_sha256|原调用的tool_snapshots/序号/before及tree_sha256(tree_identity(before))；不能用执行后的目录替代|
|target_text|调用方提供的原始候选文本，含唯一生产stop；程序不补内容、参数或答案|
|reviews|至少两个不同审核者的accepted、visible_evidence_only声明，绑定input_sha256与target_sha256|
|checks|预先确定的外部验证argv列表；仅在验证副本执行，不进入模型输入|
|check_timeout_seconds|每个验证命令时限，默认30秒，最多120秒；不是整个验证过程的硬预算|
|output|新的实验输出目录|

输入通过现有replay_run和生产构造重建；重放现在拒绝重复或未配对的生成记录。源调用必须能唯一绑定before快照；相同参数多次出现而无法唯一定位时拒绝，不猜测快照。仅接受RWKV独立或有建议来源，不把strong takeover当RWKV纠正来源。审核者身份是可信流程提供的声明，本检查器不能证明两个名字背后是独立的人/模型。

验证先复制两份原快照：第一份跑原检查，要求命令实际返回且至少一项非零；第二份执行原样候选，要求文件内容确实改变。再复制修改后的产物供同一组检查执行，要求全部真实退出0且工具成功。测试副本的写入不会被回填到候选产物。找不到程序、无变化写入、未通过测试分别记录，不伪装成通过。

validated_candidate表示该来源绑定、原子修改和固定检查通过，并非普遍语义正确或已进入训练。training_admitted始终为false；还需来源家族切分、去重、覆盖、授权版本及训练manifest。现有direct训练freeze仍只接受原有读取/摘要标签，本轮没有以不兼容字段悄悄扩展历史数据集。不能把后续测试结果写进这次生成的输入，也不能训练模型虚称它已经执行过外部检查。

## 账本解释

读取任务目录中的model_trace、strong_trace和ADVICE_PROVIDER_TRACE，排除workspace、工具快照和PARENT_TRACE副本。跨恢复任务比较时显式包含原父运行目录；单次续跑账本不冒充完整项目成本。

- provider_attempts包含已登记但没拿到usage的失败尝试。以run_id/call_id/attempt去重；冲突记录拒绝。
- provider_input/output_tokens是供应商usage。缺失、布尔值、负数或非整数视为未知。
- logical_*是原始token ID记录的逻辑输入/输出；完整上下文长度不是native State增量计算量，不当作实际GPU费用。空token数组也不自动代表零输出。
- 可提供rates JSON，含currency及rates（模型名→input_per_million/output_per_million）。它是明确的统一单价估算，不推断缓存折扣、阶梯价或在线价格。
- known_cost_subtotal只加有usage且有单价的尝试，须结合priced_attempts看；其值为0不表示任务免费。缺任一费用证据，total_cost为null。
- 当前model与provider日志没有统一计费调用ID，混合账本不按调用数量猜配对。即便供应商usage齐全，含未计价native调用的总费用仍未知。
- end_to_end_seconds来自最外层交付记录；旧内层elapsed单列，不把子阶段耗时相加冒充墙钟。任务的assistance、termination、acceptance原样保留，不据final_answer推断验收通过。
- 远端GPU秒、峰值显存仍为null。本轮不是项目总成本/吞吐测量完成，也不据此宣称便宜或并发收益成立。

后续在获准真实任务中完善原生服务用量与调用身份，外部按同质量交付计算每个合格任务成本。工程增强不构成无限延期StateTune的理由；训练门槛见统一StateTune计划。

## 原样候选审核（离线）

`review-packet --input /absolute/original-input.txt --candidate /absolute/raw-candidate.json` 打包原始输入和候选；`review-check --packet /absolute/packet.json --judgment /absolute/review.json` 检查审核引文、身份和判断一致性。仍通过上述同一脚本调用，输出JSON；退出0仅表示校验完成，必须读取accepted，不代表训练准入。

唯一离线说明/构造函数为 rwkv_lh/correction_review.py 的 REVIEW_INSTRUCTION / build_review_packet。最终回答与下一步工具调用分别审核，参数/答案保持原样。它不进入Controller，不取代真实测试，也不证明引用能支持断言。当前固定对照仅4/6满足预先登记判断，API错误仍被模型漏过；不得自动发布候选。[对照及来源记录](../data/experiments/RWKV_CORRECTION_REVIEW_R2_20260914/REPORT.zh-CN.md)。
