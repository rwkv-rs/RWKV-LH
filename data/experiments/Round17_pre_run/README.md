# Round17 正式运行前冻结记录

记录日期：2026-08-13；任何 Round17 RWKV 请求之前。

- 协议：`../Round17_PROTOCOL.md`，SHA-256
  `4ed24c459f08ad3ef9d63908154f63d787480b1e7f1f8b64e6a7ee697361b4c3`。
- 唯一变量：`flat_explicit_expected_mode.v5`。RWKV 必须原样提交 catalog 或 Goal mode 及其
  mode-specific 字段；Runtime 不选择、映射、补全、删改语义字段。
- 全产品测试：220/220，JUnit SHA-256
  `cf44da53b5086b55acb48b3d34d41fe03c16397733b3b073c57eabdc5f68d2e2`。
- LH-Control：30/30，results SHA-256
  `67bc4b98ab0505eee3129f87f16815a4f91740a05280d1e038130de14534c89b`。
- RWKV-E2E-90 validate-only：90 selected，`catalog_valid=true`。
- 运行前 endpoint health：available，模型
  `rwkv7-g1i-13.3b-20260805-ctx16384`，endpoint `127.0.0.1:29610/v1`。

## 冻结实现摘要

| 文件 | SHA-256 |
| --- | --- |
| `rwkv_lh/controller.py` | `c345521811b88874a0d2e31a04044838c37992f70ad38204bfb4e29351430dc3` |
| `rwkv_lh/harness.py` | `c4631b3d839da010ef54c75183207ad5c7fda8d60918df2c0a62d1108dce01d8` |
| `rwkv_lh/memory.py` | `461bfcf192e4235c975520cb34d7cac1cd50acb3d4392bcdaa3ec48141f9e797` |
| `rwkv_lh/model.py` | `5b4f427ac33131543548d0ccdfa2e950567360ea1c270a9300f501926021eded` |
| `rwkv_lh/proof.py` | `b58fa752c41ba773260c52c826cfe0002ead3e39eafd0ab52bb97529794ddabd` |
| `rwkv_lh/schema.py` | `e73188c59491d1951d65e2e97d129e067d69060257dc10149067a945f983ba69` |
| `rwkv_lh/store.py` | `d7203c0e779b25055a2e91dd0e5def792a0bf66954be233b6e638ec87e58ac05` |
| `rwkv_lh/temp_policy.py` | `778fac7645cb80388e0f3f1de8f8f22a8b08449060b99c6d317148e753daa562` |
| `rwkv_lh/witness.py` | `0194c4b467391fcedc402867d3cc841e7b497a1641dba9a0603fc56cb5b64acc` |
| `scripts/run_rwkv_e2e_benchmark.py` | `c1d5c72550788c53826ab8a332c7a2ab6265a2353d236b2442a7c6a7a9ba47a8` |
| `scripts/run_lh_control_benchmark.py` | `bb5f70e2ee2d3ebc8d13a31eb4d8484625026bc9df54415a559ca1f13f42a652` |
| `tests/test_witness_lifecycle.py` | `774c5fd3a7f288f35406a24489bc56b08ab528bd140b9755665abf20ab693b48` |

hidden acceptance/reference 在生成期禁止读取。正式 runner 必须生成 runtime doctor、完整
source-tree manifest、RUN_PROTOCOL 和 90 题全量审计。
