# RWKV Executor E5 跨工具类别单一状态合同结果

日期：2026-09-04（Asia/Shanghai）

## 结果

E5 按预注册矩阵完成 14 cases × 3 fresh zero-State attempts，共 42 次；未重跑失败样本。

- 严格通过：33/42（78.57%）
- 协议解析失败：3/42
- 重复已完成动作：0/42
- 输入长度：311–581 tokens，均值 419.21 tokens
- 结果 SHA-256：`3efff9b8a2479d2b44f398858c3d26b2d24ca2b17abfbc948f8e98b5de83db`

分类结果：

- 本地观察：9/9
- 外部检索或确定性计算：15/15
- 本地修改：9/12
- 命令执行：0/6

E5 未达到 42/42 的生产候选门槛，冻结为失败，不追加 E6。

## 失败归因

### `replace_text`

三次都选择了正确 operation，path/old/new 语义也正确，但 `arguments` 使用 Python dict 字面量的单引号；第三次还输出 Python `False`。现有边界按预注册要求不把 Python 字面量修复成 JSON，因此三次均为格式失败。这不是 state 遗忘或 completed action 重复。

### `check_command` / `run_command`

六次的 argv、cwd 与 expected exit code 内容均指向正确剩余任务，但函数名错误：五次输出 `rwkv-lh.g1j-per-stage-state-tuning.executor`，一次输出 `executor_args`。它们把输入中的 schema/role 身份片段当成调用名称，而不是使用已提交的 `check_command` 或 `run_command`。这是 operation identity 遵循缺陷，不是工具不存在，也不是 `name()` 格式。

## 最佳方案选择

按预注册的严格准确率、类别覆盖率和协议失败率，选择 E5 的“短 bootstrap + 单一最终执行状态 payload”作为当前最佳通用输入布局：

- E4 在读取类为 18/18，但只覆盖 `read_file`。
- E5 保留读取状态遵循能力，并在 14 个 operation 中有 11 个达到 3/3。
- E5 全程 0 次重复 completed action，说明单一权威状态解决了原链路的历史动作竞争问题。

生产接入只能采用 E5 的通用布局，不得增加 `read_file` 特判。命令 operation identity 与 `replace_text` 严格 JSON 两类失败应进入后续 StateTune 数据；在对应 StateTune 通过同一冻结矩阵前，不宣称 Executor 全工具完成。

## 固定身份

- 模型 SHA-256：`559371f5b9aef13189ae54b345ac096af4ad2b689996c05d89de687612b3ae65`
- State：`zero`
- State transport：`native_rwkv`
- StateTune：未使用
- 矩阵 SHA-256：`395d4753961c73cccc54cfd751f96b6602df18343091b5e69a505fe6f66d80a5`
