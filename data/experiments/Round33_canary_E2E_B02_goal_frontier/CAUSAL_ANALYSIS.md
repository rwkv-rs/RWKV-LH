# Round33 E2E-B02 Goal 收口 canary 因果分析

## 结果

- Strict E2E：`PASS`
- 外部验收：`PASS`
- Agent 状态：`completed`
- 模型请求：`8`，较 Round32 的 `11` 次减少 `3` 次
- Task / Attempt / Replan：`2 / 2 / 0`
- 逐 Task Goal binding 事件：`0`
- 逐 Task Goal provenance commit 事件：`0`
- Goal 收口 catalog / commit：`1 / 1`
- 最终交付与 `raw_rwkv_final_output` 字节级相同
- 冻结标准答案：`report.json contains exactly project Orion and doubled_count 14.`
- 固定指标：`utf8-byte-ngram-cosine.v1`，`n=5`
- 最终文本相似度：`0.457522914317`，高于 Round32 的 `0.348820847682`

相似度只用于运行后比较，没有作为在线控制信号，也没有改写 RWKV 的最终输出。

## 从后向前追踪

### 最终输出

RWKV 的最终回答说明了 `report.json` 中 `project=Orion`、`doubled_count=14`，与真实 workspace 和外部验收一致。交付层没有删改、筛选或替换模型文本。

### Goal 收口判定

在 T1、T2 都完成后，控制器只构造一次完整因果观察目录。RWKV 返回：

- GC1 的 actual source 为 T1 的真实读取观察 `M-T1-A1`；
- GC2 的 actual source 为 T2 的真实写入结果 `M-T2-A1`；
- GC3 的 actual source 为写入后的 workspace snapshot `M-T2-A1-POST-R1`。

控制器只机械校验引用存在、owner Task/Attempt 已成功、摘要未变以及 criterion 覆盖完整；criterion 与引用之间的语义选择全部来自 RWKV。

### T2：生产结果

T2 使用依赖中的真实输入值写入 `report.json`。动作结果与写后 snapshot 都被保存，局部 Task postcondition 判定为完成。此时没有逐 Task Goal criterion 提交，系统继续等到整个 active required TaskGraph 收口。

### T1：输入观察

T1 只读取 `input.txt`，局部 postcondition 判定为完成。与 Round32 不同，T1 完成后没有机会把 GC2“创建文件”或 GC3“验证文件”提前写入 Goal evidence ledger，因此没有中间状态污染。

## 与 Round32 的因果差异

Round32 在 T1 后就询问整个 Goal，RWKV 曾把一个读取观察过度绑定到 GC2、GC3；Round33 删除了这个阶段错位。现在每个 Task 只判断自己的局部 postcondition，Goal criterion 只在真实生产链收口后判断一次。

这次 canary 证明 Round33 的阶段调整对本次采样有效，但不能证明 basic 组稳定。随后相同 B02 在 Basic30 批次中因为规划多出冗余验证 Task 而阻塞，说明当前更早的规划与任务执行链仍受采样形态影响。

## 结论

Round33 修复了“中间 Task 提前提交整个 Goal”这一结构缺陷，并减少请求数。但单题 canary 不能作为上传依据；必须结合 Basic30 中的 23 个前置链路失败与 2 个 Goal 假阳性继续整改。
