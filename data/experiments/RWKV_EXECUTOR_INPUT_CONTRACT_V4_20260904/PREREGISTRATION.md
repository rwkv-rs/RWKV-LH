# RWKV Executor 单一执行状态合同预注册

日期：2026-09-04（Asia/Shanghai）

## 已冻结证据

- E1：单一尾部 `execution_state` 的 remaining path 命中 6/6，但重复实验协议标识导致 1 个 operation identity 错误。
- E2：移除 G1J 结构化 role/schema 后仅严格通过 3/6。
- E3：恢复结构化角色形状、但又在 bootstrap 投影 completed action 后严格通过 9/18；失败按用例稳定重复 completed path。
- E1/E2/E3 均冻结为失败，不进入生产。

## 唯一候选 E4

- 直接保留 E1 已验证的结构化 `execution_state` 及字段顺序。
- bootstrap 只包含 `role=executor_args`、workspace manifest 和职责说明；不包含协议版本、completed action 或 result。
- 最终 payload 使用当前稳定 `ExecutorArgsPromptV1` 前缀和生产 schema version，但该 version 只出现一次；保留 `role=executor_args`。
- completed arguments 只在尾部 `execution_state` 出现一次，不再出现在 bootstrap、fact refs 或 history 中；remaining read/write roots 与其并列。
- selected operation 在尾部 payload 只出现一次，并由最后的 current question 以字段引用，不拼接新的 operation 别名。
- 不使用 StateTune，不改变 parser/normalizer/Harness，不增加重试、规则补写、输出修复或模型调用。

## 固定运行与门槛

- 数据仍为同一六例矩阵，SHA-256 `fb5f4d1123868be513b316db9032fc3322b160c6f96c07fe6ba995fc0b32a2a3`。
- 13.3B 身份、原生 zero State、生产采样参数与 E3 相同。
- 每例 fresh zero State 独立运行 3 次，共 18 次；不得挑选或重跑失败样本。
- 18/18 必须通过既有 normalizer，operation 为 `read_file`，path 为唯一 remaining path；否则不进入生产。
- 通过后才替换唯一生产协议，并用真实 Controller 再验证，不把本矩阵当作产品通过结果。
