# RWKV Executor E4 单一执行状态合同结果

日期：2026-09-04（Asia/Shanghai）

## 结论

E4 在原生 RWKV zero State、13.3B 固定模型与生产采样参数下严格通过 18/18 次。六个同类双文件读取场景各独立运行三次，模型每次都返回注册函数 `read_file`，并使用 Controller 声明的唯一 `remaining_read_roots` 路径，没有重复 `completed_action_arguments` 中的已完成路径。

这证明此前重复读取 `pricing.py` 不是 13.3B 无法遵循显式状态，而是 Executor 输入中同时存在历史动作、原始需求和尾部状态等互相竞争的状态视图。E4 仅证明读取类输入合同成立，尚不能直接代表全部工具类别，因此不在此阶段修改生产协议。

## 固定条件

- 候选：E4
- StateTune：未使用
- State profile：`zero`
- State transport：`native_rwkv`
- 模型 SHA-256：`559371f5b9aef13189ae54b345ac096af4ad2b689996c05d89de687612b3ae65`
- 数据矩阵 SHA-256：`fb5f4d1123868be513b316db9032fc3322b160c6f96c07fe6ba995fc0b32a2a3`
- 结果 SHA-256：`8327245967e5733f35dcec6959295817cfd4bc1ef7dd3a967e2dde72a9611559`
- 采样：temperature `0.1`、top_p `1.0`、top_k `0`、presence penalty `0.0`、frequency penalty `0.0`、penalty decay `0.996`
- 运行：6 cases × 3 fresh zero-State attempts = 18 attempts

## 指标

- operation 精确命中：18/18
- remaining path 精确命中：18/18
- 严格联合通过：18/18
- completed path 重复：0/18
- 协议解析失败：0/18

## 后续边界

下一阶段必须保持相同单一状态原则，扩展到读取、写入、文本替换、命令校验、纯计算等不同参数结构。只有预注册的跨类矩阵达到统一阈值，才允许替换唯一生产 Executor 输入协议；不为 `read_file` 增加专用分支。
