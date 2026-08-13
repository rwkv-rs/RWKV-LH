# Round10 离线与确定性门禁

- 运行前产品测试：`184/184`。
- 运行前 LH-Control：`30/30`。
- Round10 RWKV-E2E-90：90/90 case、90/90 因果链完整。
- 运行后产品测试：`184/184`。
- 运行后 LH-Control：`30/30`。

运行前和运行后 Control 的逐题 audit 均保留；Control 只证明 Controller、状态、验证、恢复、幂等、依赖、
scope 与协议夹具没有回归，不替代真实 RWKV 能力结果。

- protocol SHA-256：`63a6b1db862500a06c679ec0f059ed9c666d4aa356b6cef60592ca0ef2e35c10`
- results SHA-256：`5863d7644b921f4f95e6b53fd4a66d2559c01469f95e7053003a227fc59715a6`
- reference SHA-256：`947a4b495951374b4d83a1029a2e3196e98c277e2c5d815919bdc58bf482d89b`
- pre/post Control SHA-256：`d97b5de42c0914d6b03ad02e37ba11ddd17232cdc1a3fd4addeaa82fe4bc308a` /
  `a2c5bdf33961176760b20940f537ce03e70c4e13d6253daada1d1d08de456d80`
- canonical G1i analysis SHA-256：`cb89dc5402017c165c48f6846450f84a8033fcdb2fdee58502fa050a7bb86884`
- cross-round backward analysis SHA-256：`9be6e346e530da1f5f6afaf527748c01a6b45060f66d5f3a66ea4f3a0615eec6`

Canonical G1i 与十轮反向因果分析的 hash 由各自 post-run analyzer 在生成后记录；两者只读取已经完成的
审计，不参与模型运行。
