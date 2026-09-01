# G1J 13.3B vs 7.2B Auditor 对照预注册

- 登记日期：2026-09-01；登记早于本对照的任何推理请求。
- 用户分配：只使用 GPU0 与 GPU3；停止调用 GPU1/2 服务。
- 13.3B：GPU0，`127.0.0.1:18230`，模型 `rwkv7-g1j-13.3b-20260831-ctx16384`。
- 7.2B：GPU3，`127.0.0.1:18231`，模型 `rwkv7-g1j-7.2b-20260831-ctx16384`。
- State：两者均 zero-State，每例独立 prompt，不发送 profile/checkpoint。

## 唯一工程修复

此前 7.2B 两例暴露两项输入错误：prompt 展示了不允许模型输出的 kernel 字段名；证据只有 ref，没有对应 Harness 事实。本对照使用修复后的当前代码：

1. 模型只看允许输出的六个字段，不显示 `audit_id/schema_version` 等 kernel 字段。
2. 每个 evidence ref 显示有界 `action/status/result/artifact/revision` 事实。
3. 非 final schema 的 verdict enum 只有 `continue/repair`。
4. 使用产品 stop suffix，唯一 `current_question` 在尾部。

## 固定数据与判定

- 两例：`settings.toml/A00001` clean；`service.log/A00007` parser-retry。
- 两例事实均为完整成功 `read_file` observation。
- 期望：严格六字段 `continue`、`step_id=S1`、`step_complete=true`、绑定对应 evidence ref、`gaps=[]`。
- 每模型 gate：`2/2`。parser 或多余字段为 `output_protocol`；parser 通过但 verdict/completion/ref 不匹配为 `semantic_quality`。
- 资源决策：若 13.3B 与 7.2B gate 相同，优先复用 13.3B 驻留权重并保持独立 Auditor session/State；仅 7.2B 明显更好时推荐额外常驻 7.2B。
