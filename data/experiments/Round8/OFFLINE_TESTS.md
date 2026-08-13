# Round8 离线与确定性门禁

- 执行环境：WSL `UbuntuRecovered`
- 运行前离线：`182 passed in 10.76s`
- 运行前 LH-Control：`30/30 passed`
- 运行后离线：`182 passed in 10.71s`
- 运行后 LH-Control：`30/30 passed`

回归确认 Phase B 输入不含四个 input-only metadata key；输出 binding 的 exact fields、arguments、transforms、
criterion/order、operator merge、proof replay、历史 schema、恢复、隔离与并发边界均保持不变。

## 摘要

- 预注册协议 SHA-256：`8b396ef4d22480031d6f63d505725b5703f7a0058ca896e9463409d349c2219f`
- E2E results SHA-256：`619bcfb1f3c065d2c5a3992a60fe3026490ec0dddfea56e78f50d30349d5b4aa`
- binding analysis SHA-256：`7e5ae0eeaddf86cbd93a622e45ee22af5d73914aebb83ab4b36569ff44b8296c`
- pre/post Control SHA-256：`c97f9178e56e0ef98f9b51a11050c3c7137a0cc7f871f469e8afce56bde8e1af` /
  `8b77d3c0cf2eda3eae141491db055f3ec03f38e8a6e00f88dd4923b0a4c79914`
- Codex reference SHA-256：`947a4b495951374b4d83a1029a2e3196e98c277e2c5d815919bdc58bf482d89b`
