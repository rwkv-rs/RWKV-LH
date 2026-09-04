# 当前问题末置运行时不变量补充登记

日期：2026-08-29（S59 × G3/G4 真实 Harness 因子实验启动前）

## 原因

用户要求当前 RWKV 的所有实际生成输入都采用同一布局原则：稳定协议、状态、工具合同与证据在前，当前真实问题紧邻续写点。S59 的 Selector V6 已在服务端校验这一布局，Executor 的冻结验证器也已检查每次生成输入；本补充把相同检查加入实际 Executor 调用边界，避免未来调用路径绕过离线验证器。

## 变更边界

- `rwkv_lh/model_io.py` SHA-256：`9a4880955c84c20e11f2022acb1416e65641f2aafaee6f8eb86aa57a60c9723c`。
- `rwkv_lh/model.py` SHA-256：`747f41952d61b492c25616add19a703f90a85e2425ea6d9a2113318346be954c`。
- `tests/test_current_rwkv_input_layout.py` SHA-256：`650a706824e896fd69b556473611961f55cda2fb4045e9dd5bd704e7dd4ac662`。
- 定向回归：`uv run --no-project --python 3.13 pytest -s -q tests/test_current_rwkv_input_layout.py tests/test_independent_network_selector_integration.py tests/test_model_session.py`，44/44 通过。

该变更不改变任何已经冻结的 Selector 或 Executor 输入字节、模型、state、采样参数、数据、指标、阈值或选择规则；它只在 13.3B 请求发出之前机械验证既有布局。验证失败时不调用模型。它不读取、诱导、修改、删除、重排或隐藏任何 RWKV 原始输出。

## 固定运行时门禁

独立 Selector/Executor 架构中的每个 Executor 生成输入必须满足：

1. 恰好一个已提交工具合同；合同 JSON 的最后字段为完整的 `current_requirement`。
2. 普通调用中该合同紧邻 `Assistant: ```json` 续写点。
3. 协议拒绝重试中，原合同保持不变；精确拒绝事件之后追加的 retry JSON 最后字段为非空 `current_question`，并紧邻续写点。
4. 完整要求与当前 Goal 精确相等；Selector 和 Executor 仍为不同 lane、不同 state。

该门禁作为安全不变量加入随后的固定因子消融与发布验证，但不改变预注册评分口径。
