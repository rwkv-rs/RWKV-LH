# Round11 离线、确定性与正式门禁

## 正式 E2E 前

- 实现后完整产品测试：`190/190`。
- LH-Control-30：`30/30`。
- pre-run Control results SHA-256：
  `39787467a0875c9b372723c454ebf09ac9603416348400140970c144c5451e79`。

## 正式 E2E 后（保持 Round11 代码不变）

- 完整产品测试：`190/190`，12.45s。
- LH-Control-30：`30/30`。
- post-run Control results SHA-256：
  `4e0f835370ab5fd92e82555e7032ee84968aba938fac588c72dc867087e68397`。
- RWKV-E2E-90：90/90 case，90/90 因果链完整，每题 `audit/model_trace/event_log/state_timeline`
  全齐。

## Post-run capsule 边界修复后

- 完整产品测试：`190/190`，12.27s。
- LH-Control-30：`30/30`。
- post-fix Control results SHA-256：
  `33841b42135c12c48e2a6b3d55021c2e4f5f60415c2111add40eaeb1fb234749`。
- 专项回归同时校验 `projection.capsule_tokens == 完整 capsule 实际 RWKV token 数`
  且 `<=5000`。

## 固定哈希

- 预注册协议：`d1fc898bd04e2fbc777ea527c217b440ef2924d012757aaec56d465e173310cc`。
- 正式 results：`dedcc2db250b3a563d5cb6271596a2a941a4ca6900452cdf631b24164fbeedbf`。
- Codex 标准答案：`947a4b495951374b4d83a1029a2e3196e98c277e2c5d815919bdc58bf482d89b`。
- 通用因果分析：`30ba0f311f6812fb3256875851af95ae0454bef77cf1f25fef409dd7fb4c5cb1`。
- Round1--11 反向因果分析：
  `c915bf7360ab6ff8e8ac9db95dfab26012203e807517638b9dda982895954463`。
- Round11 持久义务分析：
  `4338b6e2698368a56777856bf3da50fc0bd27f05a23dd1647de3efc512a2373e`。

Control 只证明 Controller、状态、验证、恢复、幂等、依赖、scope 和协议夹具无回归；
不替代真实 RWKV 能力成绩。

