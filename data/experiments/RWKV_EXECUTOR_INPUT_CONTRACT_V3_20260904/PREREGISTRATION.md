# RWKV Executor 匹配角色形状的状态尾部合同预注册

日期：2026-09-04（Asia/Shanghai）

## 已冻结前序结果

- 旧生产布局：真实第二轮重复 completed path。
- E1：remaining path 6/6，严格 operation+path 5/6；一个输出把重复的实验协议标识当作函数名。
- E2：operation 6/6，严格 operation+path 3/6；去掉 G1J 的结构化角色形状后，三例重复 completed path。
- E1/E2 均已冻结为失败，不进入生产。

## 唯一候选 E3

- 保留当前 G1J 已登记的 `ExecutorArgsPromptV1` 前缀、schema version、`role=executor_args`、selected operation/tool contract、committed refs、executor history 和 Tool Call generation anchor。
- bootstrap 保留当前 independent Executor 的结构化任务状态形状，但 prior action 只投影 operation、arguments、success/complete，不携带本次参数选择不需要的文件全文。
- 在 `executor_history` 后、`current_question` 前新增唯一结构化 `execution_state`：completed action arguments、remaining read/write roots、completion precondition、constraints。
- `current_question` 位于最后，要求 operation identity 严格等于 `selected_operation`，并从 remaining roots 填一个参数，不得重复 completed arguments。
- 不改变 parser、normalizer、Harness、工具 schema、模型、State、采样或评价标准；不增加重试、规则补写、输出修复或 StateTune。

## 固定数据与运行

- 继续使用冻结六例矩阵 `RWKV_INPUT_CONTRACT_ABLATION_V1_20260904/EXECUTOR_E1_MATRIX_FREEZE.json`，SHA-256 `fb5f4d1123868be513b316db9032fc3322b160c6f96c07fe6ba995fc0b32a2a3`。
- 模型固定为 `rwkv7-g1j-13.3b-zero-state-capability-ctx16384`，SHA-256 `559371f5b9aef13189ae54b345ac096af4ad2b689996c05d89de687612b3ae65`，原生 State，zero profile。
- 采样固定为生产参数：temperature `0.1`、top-p `1.0`、top-k `0`、presence/frequency penalty `0`、penalty decay `0.996`。
- 为测量生产采样可靠性，每例从 fresh zero State 独立运行三次，共 18 次；不得挑选或重跑失败样本。

## 固定门槛

- 18/18 均须通过现有 direct-call normalizer，operation 为 `read_file`，path 为唯一 remaining path；协议拒绝为 0。
- 若任一失败，E3 不进入生产且本实验停止；不得修改矩阵、次数、采样或阈值。
- 若通过，才替换唯一生产 Executor-Args renderer，并运行单元、完整回归、真实 controller 反事实和完整 Capability Ladder。
