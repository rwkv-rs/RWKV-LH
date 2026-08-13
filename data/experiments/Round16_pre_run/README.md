# Round16 正式运行前冻结记录

记录日期：2026-08-13；任何 Round16 E2E-90 请求之前。

- 协议：`../Round16_PROTOCOL.md`，SHA-256
  `e8e50244636ea185459bb136ee1d3f9df11e04e363e3385c4990df0d67d46f7f`。
- 唯一变量：`discriminated_expected_witness_union.v4`。expected 必须由 RWKV 以 catalog source 或
  Goal literal 判别联合二选一；Runtime 不择一、不丢字段、不补 ID/quote/value。
- 全产品测试：220/220，JUnit SHA-256
  `c0e6c141c68942b379ca68ce90f1ad89ca879f2a024688b1b7b88704e006245e`。
- LH-Control：30/30，results SHA-256
  `c5162e9af096c1e65fd34faac4d4e4631b9d5152c18892e13500a2c2153f738d`。
- RWKV-E2E-90 validate-only：90 selected，`catalog_valid=true`。

首次 pre-run 的产品测试为 220/220、数据校验 90/90，但 LH-Control 为 29/30，因为 LH-M04 模拟
模型 fixture 仍发出旧 v2 shape。原始失败记录完整保存在 `../Round16_pre_run_initial_lh29/`；只将该
fixture 更新为预注册 v3 union 后重新执行全部三门，最终结果如上。没有真实 RWKV 请求用于该修复。

## 冻结实现摘要

| 文件 | SHA-256 |
| --- | --- |
| `rwkv_lh/controller.py` | `00de0d4fd395302935962cf04edff5388588301228031f4f260338d1d8fb97da` |
| `rwkv_lh/harness.py` | `c4631b3d839da010ef54c75183207ad5c7fda8d60918df2c0a62d1108dce01d8` |
| `rwkv_lh/memory.py` | `461bfcf192e4235c975520cb34d7cac1cd50acb3d4392bcdaa3ec48141f9e797` |
| `rwkv_lh/model.py` | `11617782bb111c07308ec238f22605ce7a9a934b4b889ba25184e5fe41b2f1f0` |
| `rwkv_lh/proof.py` | `b58fa752c41ba773260c52c826cfe0002ead3e39eafd0ab52bb97529794ddabd` |
| `rwkv_lh/schema.py` | `e73188c59491d1951d65e2e97d129e067d69060257dc10149067a945f983ba69` |
| `rwkv_lh/store.py` | `d7203c0e779b25055a2e91dd0e5def792a0bf66954be233b6e638ec87e58ac05` |
| `rwkv_lh/temp_policy.py` | `778fac7645cb80388e0f3f1de8f8f22a8b08449060b99c6d317148e753daa562` |
| `rwkv_lh/witness.py` | `0194c4b467391fcedc402867d3cc841e7b497a1641dba9a0603fc56cb5b64acc` |
| `scripts/run_rwkv_e2e_benchmark.py` | `c1d5c72550788c53826ab8a332c7a2ab6265a2353d236b2442a7c6a7a9ba47a8` |
| `scripts/run_lh_control_benchmark.py` | `39af9babb4e7b7eff56d8265426cb095f815bc85638b2b6461669e68869d3654` |
| `tests/test_witness_lifecycle.py` | `8294125bd0d5613be72a53984e3770ad2d37c51372fd637b320505fa9ed4b403` |

hidden acceptance/reference 在生成期禁止读取。正式 runner 必须生成 runtime doctor、完整
source-tree manifest、RUN_PROTOCOL 和 90 题全量审计。
