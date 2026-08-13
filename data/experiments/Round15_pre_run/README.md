# Round15 正式运行前冻结记录

记录日期：2026-08-13；任何 Round15 E2E-90 请求之前。

- 协议：`../Round15_PROTOCOL.md`，SHA-256
  `cb347b976834bafceeca88cc2adf96b26ed18fcc40385735e4b1d8026e92e5eb`。
- 唯一变量：`semantic_minimal_obligation_replan.v2`。`new_tasks` 是唯一语义必需顶层字段；
  `schema_version/reason` 仅为可选审计元数据，缺失不补写。所有任务、Goal、criterion、dependency、
  scope 与 graph 校验保持 Round14 原样。
- 全产品测试：216/216，JUnit SHA-256
  `79c42d3852408e6de9576a315b8f019d697762a66c6d0225508bbd1ca30f7b46`。
- LH-Control：30/30，results SHA-256
  `fae8bff2bec23d28228a4236023131775129966f0f2b85f953d6cd3244448965`。
- RWKV-E2E-90 validate-only：90 selected，`catalog_valid=true`。

## 冻结实现摘要

| 文件 | SHA-256 |
| --- | --- |
| `rwkv_lh/controller.py` | `23c3490fc094c7ebf33ecde3f649813193674dc3e1162df82092fa7187002124` |
| `rwkv_lh/harness.py` | `c4631b3d839da010ef54c75183207ad5c7fda8d60918df2c0a62d1108dce01d8` |
| `rwkv_lh/memory.py` | `461bfcf192e4235c975520cb34d7cac1cd50acb3d4392bcdaa3ec48141f9e797` |
| `rwkv_lh/model.py` | `e0ef6fb3c1a4592e20a2c5fe4875191e649dff8dfb20a856b1775135d4e2df01` |
| `rwkv_lh/proof.py` | `b58fa752c41ba773260c52c826cfe0002ead3e39eafd0ab52bb97529794ddabd` |
| `rwkv_lh/schema.py` | `e73188c59491d1951d65e2e97d129e067d69060257dc10149067a945f983ba69` |
| `rwkv_lh/store.py` | `d7203c0e779b25055a2e91dd0e5def792a0bf66954be233b6e638ec87e58ac05` |
| `rwkv_lh/temp_policy.py` | `778fac7645cb80388e0f3f1de8f8f22a8b08449060b99c6d317148e753daa562` |
| `rwkv_lh/witness.py` | `0194c4b467391fcedc402867d3cc841e7b497a1641dba9a0603fc56cb5b64acc` |
| `scripts/run_rwkv_e2e_benchmark.py` | `c1d5c72550788c53826ab8a332c7a2ab6265a2353d236b2442a7c6a7a9ba47a8` |
| `scripts/run_lh_control_benchmark.py` | `d7e5bcad2152ff0d45b0116d1f16a24e0a447886ab75c22691190da11b60f230` |
| `tests/test_long_horizon_controller.py` | `79693d8bdc85a3942ad152cf15c10c17d6e8bf85224a15c6b022affdfe533caa` |

数据集、hidden acceptance 与 reference 使用 runner 固定的 RWKV-E2E-90 v1；acceptance/reference 在生成期
禁止读取。正式 runner 必须另行生成 runtime doctor、完整 source-tree manifest、RUN_PROTOCOL 和 90 题
全量审计。
