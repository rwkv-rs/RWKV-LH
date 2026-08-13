# Round35 五题定向 canary 因果分析

## 固定结果

- Strict E2E：`3/5`
- Agent completed：`4/5`
- External acceptance：`4/5`
- Strict PASS：B02、B06、B25
- 假阴性：B13（External PASS、Agent blocked）
- 假阳性：B29（Agent completed、External FAIL）
- 全部最终回答仍为 raw RWKV 输出字节级直通

Round33 Basic30 中这五题的 Strict 结果全部失败；Round32/33 的独立 B02 canary 曾通过，但同一题在 Round33 Basic30 中阻塞。因此本轮 `3/5` 是有意义的定向改善，但不是稳定 Basic30 结论。

## 逐题回溯

### B02：Strict PASS

本轮 3 个 Task、3 个 Attempt、12 次模型请求，真实 workspace 与外部验收正确。动作与 Task commit prompt 不再包含 `model_action`、snapshot audit 元字段或 causal-state ledger。虽然规划仍多出一个 Task，链路没有因内部字段复制阻塞。

### B06：Strict PASS

Round33 的最早错误是冗余验证 Task 的动作 prompt 暴露 `model_action`、`source_label/source_url`，纠正请求又回显错误 JSON，导致连续非法工具参数。Round35 的全部 action prompt 检查结果：

- `model_action`：0 次
- `source_label`：0 次
- `rwkv-lh.causal-state.v1`：0 次
- action argument contract rejection：0 次
- model contract error：0 次

模型完成 5 个 Task、5 个 Attempt，最终 Strict PASS。该题直接验证了阶段 capsule 隔离修复了原始放大链。

### B13：External PASS、Agent blocked

动作链本身完全正确：

1. T1 读取原始 `config.json`；
2. T2 写入 region=`cn-east`、retries=`5`，保留 service、enabled、owner；
3. T3 读取并解析最终 JSON；
4. 三个 Task postcondition 都由 RWKV 判定 pass；本次没有 Task commit schema alias 或额外字段错误。

新的最早错误出现在 Goal evidence commit。RWKV 对 7 个 criterion 都返回了语义上合理的 reason，但把 `actual_ref` 与 `expected_ref` 绑定为同一个引用。例如 GC2、GC3 使用 `M-T3-A1` 同时作为 actual 和 expected；GC4—GC6 使用 `M-T1-A1` 同时作为两侧。结构校验正确拒绝同 ref。随后 Goal obligation replan 两次输出非 canonical Task batch，最终阻塞。

这说明 B13 的 Round34 格式问题在本次采样中已经消失；当前缺陷是 Goal provenance 协议把同一批 source 同时列入 actual/expected 候选，弱模型容易复制同 ref。另一个结构限制是“同 workspace path 一律不能作为 before/after 两侧”，它会妨碍同一文件的保留性比较。这个问题必须作为独立后续轮次处理，不能由格式层删改引用。

### B25：Strict PASS

Round33 的 Goal prompt 暴露绝对 workspace root，RWKV 将它写进 constraint，后续工具参数复制绝对路径而在执行前被 Harness 拒绝。Round35 中真实 root 在完整 model trace 出现 `0` 次；GoalState 仍在运行时保存真实 root，Harness scope enforcement 未削弱。

模型使用相对路径完成 4 个 Task、4 个 Attempt，最终 Strict PASS。该题证明“runtime root 与 model-visible workspace scope 分离”修复了接口泄漏，而不是放宽路径安全。

### B29：Agent completed、External FAIL

T1 正确完整读取：

```text
immutable payload
line two
```

Round35 的 T2 action prompt 明确包含上述完整 dependency content，并且没有内部 audit 字段。但 RWKV 没有选择已注册的 `copy_file`，而是选择 `write_file`，且只把最后一行 `line two` 写入 `backup/source.txt`。这次最早错误不是上下文缺失，而是模型在完整证据与直接 copy 工具都可用时作出了错误 action/arguments。

T2 的 deterministic verifier 以 RWKV 已提交的 write content 为 expected，因此通过；Task postcondition 又错误声称“与源内容完全相同”。T4 只读取错误副本，也继续错误判定。Goal evidence 最终假阳性。架构没有修改错误文件或最终回答。

下一步可以在 action contract 中用通用原则提示：当注册工具能直接完成 copy 等原子操作时，优先使用直接操作，避免由模型重建长内容。是否采用仍由 RWKV 决定，控制器不能按任务关键词强制切换工具。同时，Task postcondition 需要更清楚地区分 dependency 原文与 action 自身 expected，避免把 action 参数自证为正确。

## 结论

Round35 已实际修复两类基础接口问题：内部状态字段复制（B06）和绝对 runtime path 泄漏（B25）。剩余两题显示的不是格式转换缺口：

- B13 是 Goal actual/expected provenance 角色与时间关系设计不清；
- B29 是 RWKV action 选择/内容复制错误，被自引用 verifier 与后续语义过度声明放大。

因此不能继续向格式层添加 coercion。应先运行固定 Basic30 测量全局影响，再分别预注册“时间独立 provenance”与“直接原子操作/非自引用 Task 判断”的后续结构实验。
