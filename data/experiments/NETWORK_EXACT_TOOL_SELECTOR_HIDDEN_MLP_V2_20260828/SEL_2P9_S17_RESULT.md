# NET-SEL-2P9-S17 结果

日期：2026-08-28  
状态：内部门未全过；不接入

## 实验问题

保持 S8 的 zero-state 描述头和全部原始 pair score 不变，只在每个原子阶段实际获授权的菜单内取 argmax。菜单来自 Harness 权限/能力投影，不由 planner 指定具体 tool。

## 固定产物

- S8 head SHA256：`36728736ce539039f5af132872edbf0f179aa66112ce57dbf16a578cf2586c23`
- learned state：无
- 完整结果：`run_s17_scoped_description_internal/RESULT.json`
- 每行菜单、digest、原始 logits 与选择：`run_s17_scoped_description_internal/SCOPED_PREDICTIONS.jsonl`

## 结果

- 25 类 test accuracy：`0.9160000`
- macro-F1：`0.9154374`
- boundary accuracy：`0.8777778`
- natural dev：`176/176`
- `web_search` recall：`28/30 = 0.9333333`
- `connector_lookup` recall：`23/30 = 0.7666667`
- `read_file` recall：`23/30 = 0.7666667`
- score values modified：`false`
- source logits preserved：`true`
- RWKV 文本生成调用：`0`；sampling 调用：`0`

accuracy、macro-F1、boundary、全类最低 recall 与 natural-dev 门通过；新功能 `connector_lookup` 的预注册 recall `>= 0.85` 门失败。外部 ECRA 未作为 S17 新盲测读取。

## 结论

按真实授权菜单投影是正确的 Harness 边界，也显著减少无关工具干扰；但它本身没有修复 connector 与其他读取工具的语义混淆。S17 只能作为后续架构基础，不能单独授权生产接入。

