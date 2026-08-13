# Round14 正式运行前冻结记录

记录日期：2026-08-13；任何 Round14 E2E-90 请求之前。

- 协议：`../Round14_PROTOCOL.md`，SHA-256
  `f2ed1cd1b9263c7338454a7ff03f44279c311be563f5eee9def93a6c1d953bb7`。
- 唯一变量：`semantic_minimal_witness_selection.v3`。`reason/note` 仅从 hard gate 降为可选审计
  文本；缺失时不补写。decision、criterion coverage、WS/WH、Goal quote/value、proof 全部不变。
- 全产品测试：212/212，JUnit SHA-256
  `801324c690fcdc34b0b5668ae1c462ae1979960ea1b19149eca66e6238e53337`。
- LH-Control：30/30，results SHA-256
  `7cd32cfa2d3bb8c8dde8c04d08aa6dd0558dff43297b9865fe1161c1067b7210`。
- RWKV-E2E-90 validate-only：90 selected，`catalog_valid=true`。

## 冻结实现摘要

| 文件 | SHA-256 |
| --- | --- |
| `rwkv_lh/controller.py` | `679d9be9cf12aa396bec0f779f338b372755e96bed985be377e8cb8456e10a68` |
| `rwkv_lh/harness.py` | `c4631b3d839da010ef54c75183207ad5c7fda8d60918df2c0a62d1108dce01d8` |
| `rwkv_lh/memory.py` | `461bfcf192e4235c975520cb34d7cac1cd50acb3d4392bcdaa3ec48141f9e797` |
| `rwkv_lh/model.py` | `9a1eee444e858ff5b220abe67a0aee897f64edce5d83cffe914786186cfccc99` |
| `rwkv_lh/proof.py` | `b58fa752c41ba773260c52c826cfe0002ead3e39eafd0ab52bb97529794ddabd` |
| `rwkv_lh/schema.py` | `e73188c59491d1951d65e2e97d129e067d69060257dc10149067a945f983ba69` |
| `rwkv_lh/store.py` | `d7203c0e779b25055a2e91dd0e5def792a0bf66954be233b6e638ec87e58ac05` |
| `rwkv_lh/temp_policy.py` | `778fac7645cb80388e0f3f1de8f8f22a8b08449060b99c6d317148e753daa562` |
| `rwkv_lh/witness.py` | `0194c4b467391fcedc402867d3cc841e7b497a1641dba9a0603fc56cb5b64acc` |
| `scripts/run_rwkv_e2e_benchmark.py` | `c1d5c72550788c53826ab8a332c7a2ab6265a2353d236b2442a7c6a7a9ba47a8` |
| `scripts/run_lh_control_benchmark.py` | `d7e5bcad2152ff0d45b0116d1f16a24e0a447886ab75c22691190da11b60f230` |
| `tests/test_witness_lifecycle.py` | `1ba10200cbc3a81e179915ab0516ee7b039e2d92a7c14683850e340cdeea9fba` |

数据与 hidden acceptance/reference hashes 与 Round13 冻结记录相同；acceptance/reference 生成期禁止读取。
正式 runner 必须另行生成 runtime doctor、完整 source-tree manifest、RUN_PROTOCOL 和 90 题全量审计。
