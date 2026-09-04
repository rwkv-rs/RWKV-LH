# RWKV Executor E5 跨工具类别单一状态合同预注册

日期：2026-09-04（Asia/Shanghai）

## 目的

E4 已在 `read_file` 双路径状态遵循上严格通过 18/18，但不能据此断言 Executor 输入合同适用于其他参数形状。E5 只检验输入合同的跨类泛化，不修改生产代码、不执行工具、不使用或训练 StateTune。

## 冻结矩阵

- 文件：`EXECUTOR_E5_CROSS_CLASS_MATRIX.json`
- SHA-256：`395d4753961c73cccc54cfd751f96b6602df18343091b5e69a505fe6f66d80a5`
- 来源：当前产品 Harness 合同的确定性合成用例；target 未使用模型输出构造。
- 规模：14 个用例，覆盖 4 个类别和 14 个代表性 operation。
- 类别：本地观察、本地修改、命令执行、外部检索或确定性计算。
- 参数形状：路径、文本、嵌套 JSON、源/目标双路径、行号、argv 数组、查询、枚举、算式、日期与时区。

## 唯一候选 E5

- 使用 E4 已验证的短 bootstrap；bootstrap 不含任务值、历史动作或工具合同。
- 所有任务值只在最终 `ExecutorArgsPromptV1` payload 出现一次。
- payload 顺序固定为：schema、role、current requirement、selected operation、selected tool contract、supporting facts、execution state、constraints、current question。
- 已完成动作仅位于 `execution_state.completed_actions`，与 remaining roots 组成一个权威状态对象；不投影到 bootstrap 或第二份 history。
- Executor 只负责为 Selector 已提交的 operation 填写参数，不允许重新选工具。
- parser、normalizer 和 Harness 使用当前生产实现；不做输出修复，不补写模型没有给出的语义字段。

## 固定运行条件

- 13.3B 模型 SHA-256：`559371f5b9aef13189ae54b345ac096af4ad2b689996c05d89de687612b3ae65`
- State transport：`native_rwkv`
- State profile：`zero`
- StateTune：禁用
- 每例使用 fresh zero State 独立运行 3 次，共 42 次；失败不重跑、不挑选。
- 采样：temperature `0.1`、top_p `1.0`、top_k `0`、presence penalty `0.0`、frequency penalty `0.0`、penalty decay `0.996`。
- 结果经现有 `direct-call-envelope.v3` 与 `action-arguments.v2` 处理后，与冻结 expected arguments 比较。

## 指标与门槛

- strict pass：operation 与冻结 operation 精确相等，且 Harness 规范化后的完整参数对象与冻结 target 精确相等。
- 生产候选门槛：42/42 strict pass、4/4 类别均为 100%、0 次解析失败、0 次重复 completed action。
- 最多只运行预注册的 3 次/例，不追加临时重试。
- 若未达门槛，E5 冻结为失败，不再继续堆叠输入版本；按严格准确率、类别覆盖率和协议失败率选择 E4/E5 中证据最好的布局，并把失败类别留给后续 StateTune 数据设计。
