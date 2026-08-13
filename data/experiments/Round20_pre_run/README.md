# Round20 正式运行前冻结记录

记录日期：2026-08-13；任何 Round20 RWKV 请求之前。

- 协议：`../Round20_PROTOCOL.md`，SHA-256
  `a25bebaa201849cd4fc5879eb736fc741d975c0daa61e120f7ccde905be73aa7`。
- 唯一变量：`unchanged_deterministic_proof_recovery.v1`。只有 cache-safe workspace digest
  未变化、既有 proof failure 是 model-written same-target lineage、RWKV 新 obligation task 的固定
  语义签名完全重复时，整份 proposal 才会被拒绝；不做部分任务筛选。
- 全产品测试：233/233，JUnit SHA-256
  `bf3e7b112fd0b41be37f9b015a7b41869100b33abf3647c13670be1981cc5a61`。
- LH-Control：30/30，results SHA-256
  `efc059a8d1b6c8a50ce97b0fc3422f5ad1ede13417603854c02aca42ee16ca92`。
- RWKV-E2E-90 validate-only：90 selected，`catalog_valid=true`。
- Round18 冻结 proof 离线重放：13 条中 4 条保留、8 条 model-write lineage 被拒绝、1 条由
  既有 artifact hash 规则拒绝；SHA-256
  `5885a7b51657406080a33c971c8e568da93d1fc694accfe092b3dd662f85db8f`。
- Round19 全量 obligation 离线重放：112 个 proposal 中 4 个在 3 题命中新规则，历史追加任务
  16 个；整份拒绝、无部分筛选；SHA-256
  `ba2d202a1a8602024ce953c0dfdd1c512a11906f4990c43ba0b027824655e5d3`。
- endpoint：`127.0.0.1:29610/v1`；模型
  `rwkv7-g1i-13.3b-20260805-ctx16384`。

## 冻结实现摘要

| 文件 | SHA-256 |
| --- | --- |
| `rwkv_lh/controller.py` | `a7d2267d29d85eb546733ecfa654e052469c0d42571ea06d36dc817dcce3ec55` |
| `rwkv_lh/model.py` | `75d71361cfd32a31d28df917b67597ec8da2e310296e045134c1d27c2f7fd973` |
| `rwkv_lh/proof.py` | `fec881b93463a1963fd9c1e371d380f97bb53cb0380a64faf19c11947c1294b8` |
| `rwkv_lh/harness.py` | `c4631b3d839da010ef54c75183207ad5c7fda8d60918df2c0a62d1108dce01d8` |
| `rwkv_lh/memory.py` | `461bfcf192e4235c975520cb34d7cac1cd50acb3d4392bcdaa3ec48141f9e797` |
| `rwkv_lh/schema.py` | `e73188c59491d1951d65e2e97d129e067d69060257dc10149067a945f983ba69` |
| `rwkv_lh/store.py` | `d7203c0e779b25055a2e91dd0e5def792a0bf66954be233b6e638ec87e58ac05` |
| `rwkv_lh/temp_policy.py` | `fb8fc262755bfdc04aea412395045d8ff2cc39e23fd38049a876c62b473ff354` |
| `rwkv_lh/witness.py` | `0194c4b467391fcedc402867d3cc841e7b497a1641dba9a0603fc56cb5b64acc` |
| `scripts/run_rwkv_e2e_benchmark.py` | `c1d5c72550788c53826ab8a332c7a2ab6265a2353d236b2442a7c6a7a9ba47a8` |
| `scripts/run_lh_control_benchmark.py` | `85025858869d1503a025b7be1c4cbf9e2f1b8cc4c6b4138aaf018d57e138d201` |
| `tests/test_long_horizon_controller.py` | `eb36f742050a8d847c16731a7d87b2a9fea419d477e5f98828f5bbb1aa9aa2ec` |
| `tests/test_criterion_proof.py` | `ca9adc3a25757c941fadfe41095b216e89ccc53cb8154a544cca1f3b0df8f648` |
| `tests/test_witness_lifecycle.py` | `d7b426081d02cdf467391fcedc402867d3cc841e7b497a1641dba9a0603fc56cb5b64acc` |

hidden acceptance/reference 在生成期禁止读取。正式 runner 必须生成 runtime doctor、完整
source-tree manifest、RUN_PROTOCOL 和 90 题全量审计。
