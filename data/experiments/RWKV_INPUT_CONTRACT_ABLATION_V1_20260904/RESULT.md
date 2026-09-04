# RWKV 输入合同零 State 消融结果

日期：2026-09-04（Asia/Shanghai）

## Executor E1

- 固定模型：`rwkv7-g1j-13.3b-zero-state-capability-ctx16384`，SHA-256 `559371f5b9aef13189ae54b345ac096af4ad2b689996c05d89de687612b3ae65`。
- 原生 State transport，zero State，未使用 StateTune。
- 单点 `pricing.py -> verify_project.py`：通过；414 tokens，生成合法 `read_file(path=verify_project.py)`。
- 冻结同类矩阵：6 例；remaining path 命中 6/6，严格 operation+path 协议通过 5/6。
- 唯一失败例仍正确填写 `path=verify_project.py`，但把输入中重复出现的 `rwkv-lh.executor-input-ablation.e1` 误复制为函数名；这不是 remaining state 遵循失败，而是可见协议标识污染 operation identity。
- E1 没达到预注册的全部通过门槛，不进入生产。

## 归因

旧生产布局在显式剩余根之前携带完整 action/result，并在它之后重述把已完成路径放在前面的原始 requirement；模型重复已完成路径。E1 把 completed/remaining state 放到生成边界后，6/6 都填写剩余路径，证明 13.3B zero-State RWKV 能遵循该结构化状态，先前失败主要是输入布局问题。

E1 同时证明协议身份不应作为高显著度自由文本值重复暴露给参数生成：模型在 1/6 中复制了该值作为函数名。后续候选必须保持相同矩阵和评价口径，只移除非任务语义标识，不得增加规则补写或输出修复。

## 文件摘要

- 矩阵 SHA-256：`fb5f4d1123868be513b316db9032fc3322b160c6f96c07fe6ba995fc0b32a2a3`。
- 单点结果 SHA-256：`c1b1dda9622f57e69825cb10d8c1cb0e131b93fbe0ddf4917a702d4e302cbe2e`。
- 矩阵结果 SHA-256：`221ac82fed900fac775cf90499a2c3a92199a1a7bb117a2619f3354423129cb9`。

Selector S1 尚未运行；不得用旧 Head v2 评价新输入协议。
