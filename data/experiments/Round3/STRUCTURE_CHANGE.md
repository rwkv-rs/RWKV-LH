# Round3：相同失败 observation 不重复 cross-check

## 唯一运行时变量

实现 `failed_equivalent_observation_suppression.v1`：内建、确定性、workspace-confined action 在
完整 workspace content snapshot 可用时生成 canonical observation digest；同一 RecoveryState
lineage 只有在之前协议有效的 RWKV `replan` 失败结论与当前 digest 完全相同时，才复用该失败结论。

`pass`、ModelProtocolError、异常、命令、自定义/外部动作、不完整 snapshot 都不缓存。复用不能
产生 pass，不能补 criterion/action/参数/答案，仍照常消耗 recovery budget，后续 retry/reselect/
replan 继续由 RWKV failure analysis 决定。原始 observation capsule、digest、首次 validation ref、
RWKV 理由和 suppression event 全部持久化。

预注册文档 SHA-256：
`68745314659aaabfa0e734a2a3be10479bf4b0d01258ec1252570fdfe3dd5ad4`。

## 数据依据

Round2 的 post-run 固定分析发现 69 次 criterion cross-check 中有 5 次在 4 题/4 任务上重复同一
观察。Prime Agent commit `a3b3e753490d0a6ed180e905200c1a6690d78608` 的 unchanged-worktree
gate 提供了状态工程参考，但本实现不依赖 Git、不缓存外部状态，也不复制其通用 Agent 形态。

## 正式全量结果

- External：4/90（Round2 8/90，变化 -4）。
- Strict：2/90（Round2 7/90，变化 -5）。
- Agent completed：11/90；FP 9（-3）；FN 2（+1）。
- Basic/Medium/Hard External：3/30、0/30、1/30。
- 因果链：90/90；completed final-output 非干预：11/11。
- 模型请求：583；本地输入/输出 token：1,210,874 / 208,495。
- 运行后离线回归：126/126；LH-Control：30/30。

## Gate 的真实触发与因果判定

- cross-check observation prepared：42；cacheable：42；
- 首次协议有效 RWKV `replan` 失败记录：8；
- 同 case/task/validation kind/digest 的重复：0；
- 实际 suppression：0。

本轮 gate 没有进入干预分支，因此请求数下降和成绩变化都 **不能** 归因于该机制。Round3 的主要
终止入口是 46 个 `plan_missing_direct_criterion_claims`、9 个错误完成、7 个 invalid plan 和
9 个 Goal criterion 超过 5；它们由本次 RWKV 输出路径造成，并非 observation reuse 结果。

## 回档判定

Round3 恢复后的 FP 门槛为不高于 Round2 的 12，本轮 FP=9 满足这一单项；但 External 4/90 和
Strict 2/90 均显著回退，也没有超过当前最佳 External 8。因此 Round3 不提交/上传为新的最佳
GitHub 回档点。代码和完整实验数据保留在工作树中，供 Round4 单变量在同一因果基础上继续。
