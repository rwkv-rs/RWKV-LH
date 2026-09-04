# Network Exact-Tool Selector Hidden+MLP v2.1 — 数据审计修订预注册

## 继承与原因

- 冻结时间：2026-08-28（Asia/Shanghai），早于 v2.1 数据生成。
- 本协议完整继承 `PREREGISTRATION.md` 的类别、split、模型、特征、训练参数、指标、门槛与 state 消融；除本文件明确列出的数据相似度投影外不得改变。
- v2 run_r0 已按原口径拒绝并永久记录。原因是完整渲染输入在每行重复相同 25-tool menu，导致不变协议字节主导语义余弦。run_r0 不重算、不覆盖、不改报。

## 唯一修订：相似度审计投影

- 数据集版本改为 `rwkv-lh.network-exact-tool-selector.v2.1`。
- 相似度算法仍为 `utf8-byte-5gram-cosine.v1`，阈值仍为同类 `0.95`。
- 审计文本固定为每行 `selector_projection` 的 canonical JSON：`task_request`、`stage_objective`、`stage_role`、`progress`。
- 冻结且所有行相同的 menu/name/description 不参与数据重复审计；menu digest 仍逐行绑定到完整模型输入并在训练/运行身份中验证。
- split、每类数量、模板、surface bank、训练/评价代码和所有通过门槛不变。
- 若 v2.1 在固定语义投影上仍存在任一 ≥0.95 的同类 pair，整批拒绝；不得自动删行、移动 split 或提高阈值。

## 完成记录

正式 manifest 必须同时记录：v2 run_r0 rejection 路径、v2.1 审计投影名称、算法、阈值、每类最大值、全局最大值、violation count、generator/protocol/data SHA。
