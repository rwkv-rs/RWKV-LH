# RWKV Executor 任务语义尾部合同预注册

日期：2026-09-04（Asia/Shanghai）

## 起点

- E1 固定矩阵的 remaining path 命中 6/6，严格协议通过 5/6。
- 唯一失败把输入中两次出现的协议标识 `rwkv-lh.executor-input-ablation.e1` 当作函数名，path 仍正确。
- E1 已冻结为失败，不修改其输入、数据、结果或阈值。

## 唯一候选 E2

- 模型、原生 State transport、zero State、采样参数、`read_file` 工具合同和六例矩阵与 E1 完全一致。
- 可见输入只保留任务语义字段；协议版本、role id、event id、fact id 等身份继续由 Controller/状态存储校验，但不作为可复制的自由文本值送入参数生成。
- bootstrap 只声明职责、workspace manifest 和“以后续执行状态为准”。
- 最终 payload 字段顺序固定为 requirement、selected tool contract、completed action arguments、remaining read/write roots、constraints、selected operation、current question。
- selected operation 与 current question 位于生成边界附近；current question 要求函数名严格等于 selected operation，并从 remaining roots 选择一个参数，不得重复 completed arguments。
- 不添加规则补写、输出修复、重试、模型调用或 StateTune。

## 固定门槛

- 数据固定使用 `RWKV_INPUT_CONTRACT_ABLATION_V1_20260904/EXECUTOR_E1_MATRIX_FREEZE.json`，SHA-256 `fb5f4d1123868be513b316db9032fc3322b160c6f96c07fe6ba995fc0b32a2a3`。
- 六例必须全部生成合法 `read_file`，且 `path` 等于唯一 remaining path；严格通过必须为 6/6，协议拒绝为 0。
- 若失败，E2 不进入生产；不得改数据、采样参数或评价口径补跑。
- 若通过，才将同一布局替换唯一生产 Executor-Args renderer，运行协议测试、完整回归、原生 controller 反事实和完整 Capability Ladder。
