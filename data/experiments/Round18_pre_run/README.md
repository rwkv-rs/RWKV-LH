# Round18 正式运行前冻结记录

记录日期：2026-08-13；任何 Round18 RWKV 请求之前。

- 协议：`../Round18_PROTOCOL.md`，SHA-256
  `d1eff75e470a5778ea84e631a2e358472564f818db80d84e259fd48a90675db8`。
- 唯一变量：`rwkv_committed_progressive_witness_disclosure.v6`。第一请求只由 RWKV 承诺 mode；
  第二请求只披露所承诺分支。Runtime 不依据证据或答案选 mode，不补删改 binding。
- 全产品测试：222/222，JUnit SHA-256
  `11d5381651ea228be4253b4b636915407a8d1afe44f01695fe510d517897bb3e`。
- LH-Control：30/30，results SHA-256
  `7da49080768771442af031d78ebd2e781b20e7aea6afd49bcd0aa74d746ca874`。
- RWKV-E2E-90 validate-only：90 selected，`catalog_valid=true`。
- endpoint：`127.0.0.1:29610/v1`；模型
  `rwkv7-g1i-13.3b-20260805-ctx16384`。

## 冻结实现摘要

| 文件 | SHA-256 |
| --- | --- |
| `rwkv_lh/controller.py` | `ad53b7e39985a6cd2afb2dcccd2a395ed06a24d83e717e2b52eeb3b1416b5f1d` |
| `rwkv_lh/harness.py` | `c4631b3d839da010ef54c75183207ad5c7fda8d60918df2c0a62d1108dce01d8` |
| `rwkv_lh/memory.py` | `461bfcf192e4235c975520cb34d7cac1cd50acb3d4392bcdaa3ec48141f9e797` |
| `rwkv_lh/model.py` | `f18ceb948cbbfc271be18f83226d0c5b1cc3c51c81beae1f47689f5647ed90fd` |
| `rwkv_lh/proof.py` | `b58fa752c41ba773260c52c826cfe0002ead3e39eafd0ab52bb97529794ddabd` |
| `rwkv_lh/schema.py` | `e73188c59491d1951d65e2e97d129e067d69060257dc10149067a945f983ba69` |
| `rwkv_lh/store.py` | `d7203c0e779b25055a2e91dd0e5def792a0bf66954be233b6e638ec87e58ac05` |
| `rwkv_lh/temp_policy.py` | `fb8fc262755bfdc04aea412395045d8ff2cc39e23fd38049a876c62b473ff354` |
| `rwkv_lh/witness.py` | `0194c4b467391fcedc402867d3cc841e7b497a1641dba9a0603fc56cb5b64acc` |
| `scripts/run_rwkv_e2e_benchmark.py` | `c1d5c72550788c53826ab8a332c7a2ab6265a2353d236b2442a7c6a7a9ba47a8` |
| `scripts/run_lh_control_benchmark.py` | `85025858869d1503a025b7be1c4cbf9e2f1b8cc4c6b4138aaf018d57e138d201` |
| `tests/test_witness_lifecycle.py` | `d7b426081d02cdf467d1dfb9f442031b097eece68c99ed964be6aef4f52bcd4e` |

hidden acceptance/reference 在生成期禁止读取。正式 runner 必须生成 runtime doctor、完整
source-tree manifest、RUN_PROTOCOL 和 90 题全量审计。
