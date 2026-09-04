# Local Dual-Model State Ablation V2 — 执行修订 2

登记时间：2026-08-29（Asia/Shanghai）  
登记时点：EXE-G2-V3-RL 训练进行中、任何 G2 checkpoint dev/E2E 结果产生之前。

## 修订原因

原协议把 `SEL-S31-R` 写入 `L10/L11`，只用于估计 Selector/Executor state 的交互项。
后续按照当前正式服务的内容寻址合同启动该组合时，服务在任何推理前 fail closed：

```text
ValueError: network Selector fused head portable identity mismatch
```

这不是分类错误，也不是性能失败。正式 S39 `concat-h64` Head 的冻结
`portable_feature_identity.state_profile` 为：

```json
{"id":"zero","sha256":"0000000000000000000000000000000000000000000000000000000000000000"}
```

而 S31 的 profile identity 是：

```json
{"id":"selector-true-trajectory-s31-step2000-v1","sha256":"1d7ab37e2ef3a87a6ff8e6792ed426f4c84694902ada62b60d15c16a6a8ce853"}
```

Head 的隐藏特征分布与 initial state 联合构成模型身份。把 zero-state S39 Head 强行接到
S31 state，会在不重新训练 Head 的情况下改变其输入分布；关闭身份校验会制造一个未经验证的
新模型。重新训练 S31 Head 又会同时改变 state 与 Head 两个变量，并违反 S31 已登记的停止条件
（固定头只改变 1/500 个决策，未达到至少 3 个的门槛，因此不得拟合新 Head）。

## 冻结后的执行矩阵

当前正式架构只运行内容身份有效的 Selector：

| 组 | Selector | Executor | 用途 |
|---|---|---|---|
| `RL00` | `SEL-Z0-S39` | `EXE-Z0-V3-RL` | request-last 零状态基线 |
| `RL01` | `SEL-Z0-S39` | `EXE-G2-V3-RL` | request-last 通用 Executor state |

`L10/L11` 标记为 **structurally invalid / not executed**，不得通过关闭校验、换 Head、类别后处理
或 13.3B 回退补跑。Selector state 的因果量继续引用已经完成的同数据固定头结果：S30 dev
`486/500 -> 487/500`，改变 1 个 raw argmax、救回 1 个、回归 0 个；其产品结论仍为拒绝。

因此本轮不再声称可估计完整四格交互项。可以回答的量是：

1. 固定正式 Selector 时，Executor V3 state 相对 zero 的离线与 E2E 主效应；
2. S31 在冻结 S30 Head 下已经测得但未达门槛的 Selector state 因果效应；
3. 多 state 联动在当前可服务身份下没有成立，不能据此增加 profile 数量。

## 同时冻结的输入协议

根据此前 RWKV 实验结论，所有当前架构 RWKV 输入遵循“证据在前、当前要求在续写点前”的
统一原则：

- Selector 保留已经验收的 S39 字节布局；工具名/描述菜单先出现，不可变任务与当前阶段目标
  后出现，当前阶段目标位于尾部附近。禁止为本轮消融改变该布局。
- Executor 使用 `independent-selector-executor.v2-request-last`：bootstrap 不含当前请求；选中
  工具合同、状态与已有证据在前，闭合 JSON 的 `current_requirement` 是最后一个字段，之后只接
  `Assistant: ```json` 续写点。
- 每个正常 Executor generation 先做干净 rollover，再且只披露一次当前要求；协议拒绝后的 retry
  以最新拒绝事件作为尾部直接原因。
- 任何重新排序仅作用于模型输入投影；服务器返回的 RWKV raw text/token IDs/finish reason/SHA
  原样追加保存，绝不诱导、修改、删除、覆盖或隐藏原始输出。

数据、阈值、相似度算法、GPU0、采样、raw 完整性和晋级门槛维持原协议及
`LOCAL_EXECUTOR_REQUEST_LAST_ABLATION_V1_20260829/TRAINING_PROTOCOL.md`，不因结果调整。
