# Post-E3 Retrieval Quality R3 预注册

登记时间：2026-08-30（Asia/Shanghai），在 R3 任何联网调用之前冻结。

## 目的与固定输入

在出站 provenance 的不完整扫描 fail-closed 修复以及 E3 Planner→Selector→Executor→Harness
工程闭环复验后，重新测量当前本地检索实现的真实发现与证据质量。沿用 R1/R2 的同一 9 例、
同一相关性定义、同一 hard gates 和同一 60 秒单动作阈值；不得根据 R3 结果修改样本、相关性
或通过条件。

- cases SHA-256：`eee343aa311811a349476f4f632b0a4a5e97cc1e6657e4c8c68255124297fd2e`；
- 基础 runner SHA-256：`795c91a4b76ced1c66bdcc2ea92e0134658a07e8acdc55c08ebf54b049129947`；
- R3 绑定 runner SHA-256：`a09afd9d3bba5446dc87b7da2506ac0f1ec6b9e165ea38ea6314b0028ae1ccf3`；
- 原始预注册 SHA-256：`b47fe1a85a2034e809104e0fdc8868b37d165a83994d0d70341997c33fb8194a`；
- provider/fetch/gateway/snapshot/runtime/actions/policy SHA-256：
  `cb8255aa2a170779150e545de9d2a807686e0c590ee7c3898ad1a6037ace427f`、
  `06fa0059a77da5cce7c85c48be8c37cef74542ab8534a2c55419fabf263831d7`、
  `067501eb5024ebf6d79e68de0be050ef0015f9c6bdb86ce866c1ad21027f6f6e`、
  `3780d064b0a5a5f3b2c1569839c9d642e996940848a3f9962cd11d57ae4d8853`、
  `39f52c282a1744c81fa62c8a14228022a600449fc658cef804943ed361f5807f`、
  `fe79f15a1e94fb030aa0f51e655aa1a2b9cd1182b3bb4cbea81913c483a66699`、
  `5b7c91a370e1134a90b7d974c0852ff327f68a4172ac3edea353ba99bb6dd1db`。

每例使用全新 snapshot 目录并只调用一次 Harness backend；模型调用为 0。Tavily key 仅从
ignored `.env.local` 读取，值不得进入报告、journal 或 snapshot。输出固定为
`run_r3_post_e3_20260830`，存在即拒绝覆盖。

## 固定通过条件

1. hard gates 9/9：status、最低 records/unique URL、相关记录、结构字段、request binding、
   snapshot 与 span locator 全部成立；
2. Tavily-required 4/4 必须由 Tavily 成功，且不得使用 Bing/DDG discovery fallback；
3. 每个动作 ≤60 秒；
4. 所有持久化 artifact 中配置凭据出现次数为 0；
5. 另外原样报告 top-1 relevance、expected-host precision、duplicate ratio、p50/p95；诊断
   指标不替代 hard gate；
6. provenance UNKNOWN/扫描不完整拒绝由已冻结 7/7 故障矩阵独立证明；R3 不把确定性覆盖
   冒充真实网络分支，也不得因 fail-closed 修复把九个明确公开查询误拒绝。

任一失败必须保留原始 provider attempts 与 snapshot 证据并扩展同类检查；不得改写 provider
返回、RWKV 输出或评价口径来发布。
