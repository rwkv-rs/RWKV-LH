# Round19 正式运行前冻结记录

记录日期：2026-08-13；任何 Round19 RWKV 请求之前。

- 协议：`../Round19_PROTOCOL.md`，SHA-256
  `556e032f727317010008d84f2823bd294841832bee59283fb40c7b3a205876df`。
- 唯一变量：`model_written_target_provenance_independence.v1`。Proof 只新增 model mutation owner 与
  actual target 的同路径 provenance overlap；不判断值、不选 source、不修改 RWKV 输出。
- 全产品测试：229/229，JUnit SHA-256
  `efdd9b4525e42306d87515a9680469cc88d03297038c8274d2f4370332d24f93`。
- LH-Control：30/30，results SHA-256
  `274ccfe89c476c4e8bf8d8ea3453c205a21a5457cbb7c90d75f66a48bb9501d8`。
- RWKV-E2E-90 validate-only：90 selected，`catalog_valid=true`。
- Round18 冻结 proof 离线重放：13 条中 8 条 model-write lineage 被新规则拒绝，4 条非写入来源保留，
  1 条由既有 artifact hash 规则拒绝；SHA-256
  `5885a7b51657406080a33c971c8e568da93d1fc694accfe092b3dd662f85db8f`。
- endpoint：`127.0.0.1:29610/v1`；模型
  `rwkv7-g1i-13.3b-20260805-ctx16384`。

## 冻结实现摘要

| 文件 | SHA-256 |
| --- | --- |
| `rwkv_lh/controller.py` | `ad53b7e39985a6cd2afb2dcccd2a395ed06a24d83e717e2b52eeb3b1416b5f1d` |
| `rwkv_lh/harness.py` | `c4631b3d839da010ef54c75183207ad5c7fda8d60918df2c0a62d1108dce01d8` |
| `rwkv_lh/memory.py` | `461bfcf192e4235c975520cb34d7cac1cd50acb3d4392bcdaa3ec48141f9e797` |
| `rwkv_lh/model.py` | `f18ceb948cbbfc271be18f83226d0c5b1cc3c51c81beae1f47689f5647ed90fd` |
| `rwkv_lh/proof.py` | `fec881b93463a1963fd9c1e371d380f97bb53cb0380a64faf19c11947c1294b8` |
| `rwkv_lh/schema.py` | `e73188c59491d1951d65e2e97d129e067d69060257dc10149067a945f983ba69` |
| `rwkv_lh/store.py` | `d7203c0e779b25055a2e91dd0e5def792a0bf66954be233b6e638ec87e58ac05` |
| `rwkv_lh/temp_policy.py` | `fb8fc262755bfdc04aea412395045d8ff2cc39e23fd38049a876c62b473ff354` |
| `rwkv_lh/witness.py` | `0194c4b467391fcedc402867d3cc841e7b497a1641dba9a0603fc56cb5b64acc` |
| `scripts/run_rwkv_e2e_benchmark.py` | `c1d5c72550788c53826ab8a332c7a2ab6265a2353d236b2442a7c6a7a9ba47a8` |
| `scripts/run_lh_control_benchmark.py` | `85025858869d1503a025b7be1c4cbf9e2f1b8cc4c6b4138aaf018d57e138d201` |
| `tests/test_criterion_proof.py` | `ca9adc3a25757c941fadfe41095b216e89ccc53cb8154a544cca1f3b0df8f648` |
| `tests/test_witness_lifecycle.py` | `d7b426081d02cdf467d1dfb9f442031b097eece68c99ed964be6aef4f52bcd4e` |

hidden acceptance/reference 在生成期禁止读取。正式 runner 必须生成 runtime doctor、完整
source-tree manifest、RUN_PROTOCOL 和 90 题全量审计。
