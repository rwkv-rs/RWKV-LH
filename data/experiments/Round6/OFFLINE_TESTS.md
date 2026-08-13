# Round6 离线与确定性门禁

- 执行环境：WSL `UbuntuRecovered`
- 运行前离线：`179 passed in 10.21s`
- 运行前 LH-Control：`30/30 passed`
- 运行后离线：`179 passed in 10.20s`
- 运行后 LH-Control：`30/30 passed`

179 项包含全部 read operator 参数化合同、未知 operator/字段、binding 数量/顺序/重复、semantic replan、
binding failure 不覆盖 semantic pass、最终 proof 重放、历史 schema、恢复、隔离与并发回归。

## 摘要

- 预注册协议 SHA-256：`d23034ec25b45947993c707a78cc10449fef830e14b9dd27a82fd74dc31c81a8`
- E2E results SHA-256：`3c0ece575ee2980551353d7b9b69561391219bdb91fab201bcce421201e2f73b`
- operator analysis SHA-256：`6aece4a0fa3a502cc5886cd36b9eb429a08659aa1cbb5877dca609bd34f3de88`
- pre/post Control SHA-256：`c4a373c353e8e603fa7183541c77bc535b1953467f59556a2f0c0d7b93a7659b` /
  `93db64996a3f07a25a6ce5e1763a799c6afe1398b0c1fc67fbb0fabc5501af99`
- Codex reference SHA-256：`947a4b495951374b4d83a1029a2e3196e98c277e2c5d815919bdc58bf482d89b`
