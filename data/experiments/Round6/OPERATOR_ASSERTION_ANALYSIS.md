# Round6 Progressive-Disclosure Read Operator 专项分析

本分析只在 90 题全部结束后执行；hidden acceptance 与 Codex reference 没有进入 Phase A、Phase B、proof
或任何 RWKV 请求。

## 结论

两阶段 progressive disclosure 证明“具体 operator 名”比 Round5 联合 source schema 更接近弱 RWKV 可用
边界，但仍没有产生一条 VERIFIED proof：External `6/90`、Strict `0/90`、Agent completed `0/90`、FP
`0*`、FN `6`。Round6 比 Round5 External 回退 6，不能上传。

## 三层漏斗

- 20 题进入 assertion pipeline，共 53 个 event：RWKV semantic pass 27、replan 26。
- Phase A 共 79 个 validation 请求，52 个 contract-error event；27 个 pass event 中形成 33 个 intents。
- Phase B 共 51 个 binding 请求，46 个 contract-error event；只有 5 个 event 绑定成功，得到 7 条 assertion。
- 7 条均 REJECTED：6 条引用的 `task_id` 不是 active task 的 direct dependency；1 条 actual workspace 与
  expected dependency artifact 最终指向同一 `metrics.json`，被独立来源检查拒绝。
- verified claim、CriterionEvidence、Agent completion 均为 0。

Phase B 首个合同错误中，37/46 是 binding 对象没有严格包含
`criterion_id/actual_arguments/actual_transforms/expected_arguments/expected_transforms`。这说明即便 read operator
参数已经渐进披露，把 actual/expected arguments 与 transforms 作为五个平行字段一次绑定，对当前 RWKV 仍然
过重。

## operator 选择本身

成功形成 intent 的 actual operator 主要为 dependency artifact JSON（15 次），其次 action-result JSON pointer
（5）、workspace JSON pointer（4）、workspace JSON（3）。expected 几乎全部选择 dependency artifact JSON
（24/33），没有选择 `goal_literal`。这不是程序选择结果；它暴露了模型偏向把当前 task 自产 artifact 误认
为 direct dependency，并经常让 actual/expected 指向相同证据。

不能把 `task_id == active task` 自动改成真正 dependency，也不能发现同源后替换 expected 为 Goal literal：两者
都会替 RWKV 作语义决定。下一步若继续 proof 路径，只能让 RWKV 在更小的协议单元内先建立可引用 evidence
handle，再由它明确选 handle；或暂时回到完成边界上游，先解决 49 题 plan obligation 阻断，使更多任务真实
执行后再评估 evidence protocol。

机器明细见 `operator_assertion_analysis.json`。
