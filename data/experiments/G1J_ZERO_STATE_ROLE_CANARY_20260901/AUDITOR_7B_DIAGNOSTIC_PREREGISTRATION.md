# G1J 7.2B Auditor zero-State 诊断预注册

- 登记日期：2026-09-01；登记早于本诊断的任何 7.2B 推理请求。
- 原因：产品一致性 13.3B 诊断在 generation 前发现 `rwkv-8222:18183` 已切换为 G1J 7.2B。13.3B 请求的模型身份 404 仅记录为基础设施阻断，不更改模型名继续运行。
- Auditor 权重：`/mnt/nas-model/g1j/rwkv7-g1j-7.2b-20260831-ctx16384.pth`，字节数 `14,400,007,869`，SHA-256 `e3091a579c23ea7ebce9a0ad1ecfbda27082eeecd64d7f0474016e626df8f9c3`。
- 服务模型身份：`rwkv7-g1j-7.2b-20260831-ctx16384`。
- State：不发送 State profile、State ID 或 checkpoint；每例独立完整 prompt。
- Prompt：本轮当前 `rwkv-lh.role-pure-goal-audit.v1` 模板，并发送产品 `JSON_CALL_STOP_SUFFIXES`。

固定两例与 13.3B 产品一致性预注册中的 Audit clean/retry 相同。parser 与语义判定也相同；gate 为 `2/2`。本诊断只评价 7.2B Auditor 角色，不评价 Executor，不启动 State Tuning。
