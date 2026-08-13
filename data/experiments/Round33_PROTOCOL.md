# Round33 预注册协议：Goal 收口证据阶段

## 触发证据

Round32 的 E2E-B02 虽然 Strict E2E 通过，但 T1 读取输入后，RWKV 提前把 GC2“创建 report.json”和 GC3“验证 report.json”提交为 verified evidence。T2 完成后，RWKV 在完整因果链上给出的绑定才合理。详见 `Round32_canary_E2E_B02_compact_replan/CAUSAL_ANALYSIS.md`。

## 单一结构变更

移除在线链路中的逐 Task Goal criterion 绑定与逐 Task Goal evidence commit。保留以下两个职责边界：

1. 每个 Task 完成后，RWKV 只判断该 Task 自己的 postcondition；
2. 当 active required TaskGraph 收口后，RWKV 才基于全部 completed active Task 的真实观察，一次性对当前缺失的 required Goal criteria 返回 `pass + bindings` 或 `replan + []`。

控制器只负责：

- 构造确定性的完整观察目录；
- 校验 criterion id 覆盖、引用存在、Task/Attempt 已真实完成、摘要未变、actual/expected 非同一引用且不共享 workspace 路径；
- 按 RWKV 选择的 `actual_ref` 机械记录 producer Task 和 Attempt；
- 证据不足时进入现有 Goal obligation 扩展。

控制器不得从 Task 标题、action 类型、criterion 文本或验收结果推断语义绑定，不得补 criterion、引用、reason、expected value 或答案。

## 协议

- 请求类型：`goal_criterion_evidence_commit`
- 输出对象仅允许 `decision` 与 `bindings`。
- `decision=pass`：对当前全部 missing required criterion 恰好各绑定一次。
- `decision=replan`：`bindings=[]`。
- 每项 binding：`criterion_id`、`actual_ref`、`expected_ref`，可选原样保存的 `reason`。
- 格式归一化不参与该固定 JSON 决策；不得为缺失字段补值。

## 预期影响

- 中间读取/发现/准备 Task 不再获得提前完成整个 Goal 的证据提交入口。
- B02 从每个 Task 两次 Goal 语义请求缩减为因果链收口时一次请求。
- 并行多文件任务只有在所有 required 文件读取、逐文件总结与聚合 Task 完成后，才进入 Goal evidence commit。
- 模型仍然拥有唯一的语义决定权；架构只改变提问时机和证据作用域。

## 固定验证

1. 单元测试：中间 Task 完成不产生 Goal criterion/evidence 事件；收口前不得生成 CriterionEvidence。
2. 单元测试：收口目录包含所有且仅包含 completed active Task 的观察，覆盖并行 sibling 和传递依赖；pending/inactive/failed 排除。
3. 单元测试：unknown ref、重复/遗漏 criterion、同 ref、同 workspace 路径、缺失 Attempt 一律拒绝；optional reason 不得生成。
4. 单元测试：证据按 RWKV 选择的 actual source owner 记录并可在 workspace 变化后失效。
5. 历史恢复：完成 Task 后崩溃，恢复时只在收口阶段提交一次 Goal evidence。
6. 大项目结构 fixture：31 文件全部读取、逐文件总结、聚合完成后才允许 Goal evidence；最大 ready frontier 仍为 8。
7. 固定离线回归：全量 pytest、LH-Control 30/30、E2E-90 validate-only 90/90。
8. 真实验证顺序：E2E-B02 canary；若因果链正确，再运行 basic 组，最后运行完整 E2E-90。
9. 最终输出继续要求 raw RWKV 字节级直通；使用冻结的 `utf8-byte-ngram-cosine.v1` 做运行后比较。

## 成功判据

- 不再出现逐 Task `task_criterion_binding` 或 Task-local Goal provenance commit 在线事件。
- 中间 Task 不能产生 verified Goal evidence。
- 收口提交中每条 claim 的语义字段全部来自 RWKV，controller 生成字段仅限引用解析、owner/attempt 映射、摘要和状态记录。
- 不降低 LH-Control、E2E-90 catalog、边界/异常/恢复回归结果。
- 真实 canary 的 Strict E2E 通过，且不存在 T1 提前声明 GC2/GC3 的状态污染。
