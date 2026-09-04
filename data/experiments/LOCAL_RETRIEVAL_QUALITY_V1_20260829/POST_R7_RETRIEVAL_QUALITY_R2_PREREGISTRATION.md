# Post-R7 Retrieval Quality R2 预注册

登记时间：2026-08-30（Asia/Shanghai），在本轮任何联网调用之前冻结。

## 目的与固定口径

在 deterministic CMix R7 门禁通过后，重新测量当前本地检索实现的真实质量，回答它是否可作为
第一正式简体版的发现与证据内核。沿用 `PREREGISTRATION.md` 的同一 9 例、同一相关性定义、同一
hard gates 和 60 秒单动作阈值，不根据本轮结果改变样本或评价。

- cases SHA-256：`eee343aa311811a349476f4f632b0a4a5e97cc1e6657e4c8c68255124297fd2e`；
- runner SHA-256：`795c91a4b76ced1c66bdcc2ea92e0134658a07e8acdc55c08ebf54b049129947`；
- 原始预注册 SHA-256：`b47fe1a85a2034e809104e0fdc8868b37d165a83994d0d70341997c33fb8194a`；
- 当前 provider/fetch/gateway/snapshot SHA-256：
  `cb8255aa2a170779150e545de9d2a807686e0c590ee7c3898ad1a6037ace427f`、
  `06fa0059a77da5cce7c85c48be8c37cef74542ab8534a2c55419fabf263831d7`、
  `067501eb5024ebf6d79e68de0be050ef0015f9c6bdb86ce866c1ad21027f6f6e`、
  `3780d064b0a5a5f3b2c1569839c9d642e996940848a3f9962cd11d57ae4d8853`。

每例使用全新 snapshot 目录、只调用一次 Harness backend；模型调用为 0。API key 只从 ignored
`.env.local` 载入，值不得进入任何报告或 snapshot。

## 固定通过条件

1. hard gates 9/9：status、最低 records/unique URL、相关记录、结构字段、request binding、snapshot
   与 span locator 全部成立；
2. Tavily-required 4/4 由 Tavily 成功且不使用 Bing/DDG discovery fallback；
3. 每个动作 ≤60 秒；
4. 凭据在所有持久化 artifact 中出现次数为 0；
5. 另外如实报告 top-1 relevance、expected-host precision、duplicate ratio、p50/p95；这些诊断指标
   不替换 hard gate。

本轮失败必须保留并扩展到同类来源；不得改写 provider 返回或通过改评价口径发布。
