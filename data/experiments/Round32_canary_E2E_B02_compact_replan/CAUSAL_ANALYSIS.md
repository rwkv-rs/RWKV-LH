# Round32 E2E-B02 逐环节因果分析

## 结果

- Strict E2E：`PASS`
- 外部验收：`PASS`
- Agent 状态：`completed`
- 模型请求：`11`
- Task / Attempt / Replan：`2 / 2 / 0`
- 最终输出：交付文本与 `raw_rwkv_final_output` 字节级完全一致；控制器没有删改、重排或替换 RWKV 输出。
- 冻结标准答案：`report.json contains exactly project Orion and doubled_count 14.`
- 固定指标：`utf8-byte-ngram-cosine.v1`，`n=5`
- 最终文本相似度：`0.348820847682`

相似度低的主要原因是 RWKV 输出了较长的思考和审计说明，而冻结标准答案只有 64 个字符。该结果仅在运行后比较，没有反馈给模型，也没有通过改写最终输出来提高指标。

## 从后向前追踪

### 最终输出

RWKV 最终报告中的 `Orion`、`7`、`14`、`report.json` 与实际 workspace 一致，外部验收也通过。最终回答本身不是本题失败源。

### Goal 完成判定

控制器在 T2 完成后发现所有 required Task 已完成，并且 GC1、GC2、GC3 都已有 verified CriterionEvidence，于是允许 RWKV 生成最终回答。这个完成条件同时检查 TaskGraph 和证据覆盖，所以 T1 的错误证据没有让尚未执行的 T2 被跳过。

### T2：真实写入和最终因果链

T2 的 `write_json` 真实创建了 `report.json`，内容恰为：

```json
{"project":"Orion","doubled_count":14}
```

RWKV 在 T2 后再次选择 GC1、GC2、GC3，并分别把：

- GC1 绑定到 T1 的真实读取观察 `M-T1-A1`；
- GC2 绑定到 T2 的真实写入观察 `M-T2-A1`；
- GC3 绑定到 T2 写入后的 workspace snapshot `M-T2-A1-POST-R1`。

这些绑定与完整因果链一致，说明模型在看到最终生产结果后能够作出合理的证据选择。

### T1：最早出现错误的环节

T1 只读取了 `input.txt`，实际观察为 `project=Orion`、`count=7`。局部 Task postcondition 判定正确：读取任务已经完成。

错误从下一步 `task_criterion_binding` 开始：RWKV 选择了 `GC1,GC2,GC3`，不仅声明“读取输入”成立，还提前声明“创建 report.json”和“验证 report.json”成立。随后 `criterion_evidence_commit` 又用同一个 T1 读取观察对三项条件全部提交证据。控制器只校验引用范围、摘要、路径独立性和覆盖结构，不理解 criterion 描述，因此三条语义过度声明都进入了 verified 状态。

### 为什么错误会被放大

这是模型错误与流程位置错误共同产生的：

1. RWKV 把“已取得后续所需值”误判为“后续创建与验证已经完成”；
2. 架构在每个 Task 结束时都要求模型面向整个 Goal 绑定 criterion；
3. 同一 Task 随后又执行一次 provenance commit，把语义选择转成正式状态；
4. 控制器的结构校验只能证明引用真实、未篡改、来源在因果范围内，不能证明一段读取内容在语义上等价于“文件已经创建”；
5. 因而一个本来不必发生的中间判断，污染了后续 Goal evidence ledger。

控制器不能通过关键词或 action 类型替 RWKV 删除 GC2/GC3；那会变成规则替模型筛选答案。正确修复点是取消中间 Task 对整个 Goal 的证据提交机会。

## 根因结论

Round32 证明了紧凑 replan 和格式边界能够让 B02 严格通过，但也证明现有“Task 局部验收 → Task 绑定 Goal criterion → Task 提交 Goal evidence”存在阶段错位。局部 Task 应只提交自己的 postcondition；Goal criterion 应在 required Task 因果前沿收口后，基于完整、真实、可审计的观察链一次性由 RWKV 决定。

因此 Round32 只作为有效 canary 和根因证据保存，不能据此宣称架构已经稳定，也暂不上传为更优最终版本。
