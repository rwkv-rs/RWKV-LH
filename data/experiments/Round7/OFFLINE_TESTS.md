# Round7 离线与确定性门禁

- 执行环境：WSL `UbuntuRecovered`
- 运行前离线：`182 passed`
- 运行前 LH-Control：`30/30 passed`
- 运行后离线复核：`182 passed in 10.47s`
- 运行后 LH-Control 复核：`30/30 passed`

182 项包含空/非空 obligation ledger、supplemental dependency 对 base/new local id 的引用、重复 existing id
拒绝、combined graph 重写、coverage 不完整拒绝、obligation assignment 不生成 evidence、历史 schema、恢复、
隔离与并发回归。

## 摘要

- 预注册协议 SHA-256：`11bcb15312555e81b6e9bcfc809f2a9131c4863663b77a2f89ceb56389e296d1`
- E2E results SHA-256：`a2292aa6f873c26b862742e3f91c32ab30eb611333fbf5871800cc5c9b022076`
- obligation analysis SHA-256：`3b54a1ef1c0226c4fdd2d31bcabd96647eaa7e7417d3db61f0744995d78d1550`
- pre/post Control SHA-256：`b60a308dbab11fbcf6c814c8036227461f57afb14fb8970d4279b5975eb69e5f` /
  `a8ded2006bc2890bba03d509df697025edbb4e731ae8289767be54c1f28f9167`
- Codex reference SHA-256：`947a4b495951374b4d83a1029a2e3196e98c277e2c5d815919bdc58bf482d89b`
