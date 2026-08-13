# Round13 正式运行前冻结记录

记录日期：2026-08-13。此目录在任何 Round13 RWKV-E2E-90 请求之前生成。

## 唯一变量与不作弊边界

- 预注册协议：`../Round13_PROTOCOL.md`
- 协议 SHA-256：`416ec0fcf6b583e796b0b0079c860d894a1f22932393da45eb0ba201b608a12e`
- 唯一变量：`post_action_catalog_bound_witness.v2`
- Controller 不生成 criterion、source、Goal literal、handle 或答案；它只投影 RWKV 已保存的
  TaskGraph ID，并逐字展开 RWKV 选择的 WS/WH ID。
- hidden acceptance 和 Codex reference 在生成期禁止读取，运行结束后才比较。

## 离线门禁

- 全产品测试：`212 passed in 12.83s`；JUnit SHA-256
  `8833a53997908c869d0ab5595eb1bfeea528f69eb5a12a71612faa6cf1bae0b1`。
- RWKV-E2E-90 数据校验：90 selected，`catalog_valid=true`。
- 第一次 LH-Control 保存在 `lh_control_30/`，29/30，results SHA-256
  `133428c31e133671eb44b000d4f8eb4fde029aae65ff4901fb159b83dc1e5866`。唯一失败 LH-M04
  是 Round12 `SequenceClient` 仍向新的 v2 selection 请求返回旧 precommit payload；失败记录没有
  覆盖，也没有放宽产品 parser。
- 更新确定性夹具后，`lh_control_30_final/` 为 30/30，results SHA-256
  `2af0d4fb28a2034624accf5b2fe5476472aed796afc09aeafc83f738ca462baa`。M04 真实顺序为
  action result → `witness_selection` → `witness_handle_binding` → proof passed → VERIFIED
  CriterionEvidence → final，且 action 只执行一次。

## 冻结核心摘要

| 文件 | SHA-256 |
| --- | --- |
| `rwkv_lh/controller.py` | `c2c401ad0e73568bb04e8b356ac6e46ba7106091092642ae3c15de5977077898` |
| `rwkv_lh/harness.py` | `c4631b3d839da010ef54c75183207ad5c7fda8d60918df2c0a62d1108dce01d8` |
| `rwkv_lh/memory.py` | `461bfcf192e4235c975520cb34d7cac1cd50acb3d4392bcdaa3ec48141f9e797` |
| `rwkv_lh/model.py` | `cd26e0ac1c608769f3b985f017a85eabb7c411c21381f6aaf01d8e55ea0a2866` |
| `rwkv_lh/proof.py` | `b58fa752c41ba773260c52c826cfe0002ead3e39eafd0ab52bb97529794ddabd` |
| `rwkv_lh/schema.py` | `e73188c59491d1951d65e2e97d129e067d69060257dc10149067a945f983ba69` |
| `rwkv_lh/store.py` | `d7203c0e779b25055a2e91dd0e5def792a0bf66954be233b6e638ec87e58ac05` |
| `rwkv_lh/temp_policy.py` | `778fac7645cb80388e0f3f1de8f8f22a8b08449060b99c6d317148e753daa562` |
| `rwkv_lh/witness.py` | `0194c4b467391fcedc402867d3cc841e7b497a1641dba9a0603fc56cb5b64acc` |
| `scripts/run_rwkv_e2e_benchmark.py` | `c1d5c72550788c53826ab8a332c7a2ab6265a2353d236b2442a7c6a7a9ba47a8` |
| `scripts/run_lh_control_benchmark.py` | `d7e5bcad2152ff0d45b0116d1f16a24e0a447886ab75c22691190da11b60f230` |
| `scripts/analyze_rwkv_round.py` | `345a5e3d7d9eb618ef2d8165f323d8f9276947a0e612beb5117aa09da0ae82c9` |
| `temp/analyze_round12_interrupted_backward_causality.py` | `70813e00cdac0fff8e38d318efad5efa081bd76c6e87d1ffbfe3a6600a015ff8` |
| `tests/test_witness_lifecycle.py` | `5943589058b02b07d259c0a744417089b1cd97548739ec73485110f391439006` |

## 固定数据

数据仍为 RWKV-E2E-90 v1，Basic/Medium/Hard 各 30：

| 资源 | SHA-256 |
| --- | --- |
| core30 visible tasks | `0bf73c9a86bd014f5a94e5686ffe744bbef6c560f4227e37d0b753b900481c4c` |
| core30 hidden acceptance | `c4953c556a9ba2e080493f34bb2261db349080542376c4e94f08d5227e0f74cd` |
| lh12 visible tasks | `d813a7bc3a42e27ee3573ea342a918bd7ee5347ca8b0e893c04fded262457a5e` |
| lh12 hidden acceptance | `976e075bcc81780ed38ce7b9fe8c6c19c1b239bb72595ce176308f2760a0cd9f` |
| extension48 visible tasks | `384d52b5395dbcb31947dbfd1cfe63167ccbe68ed8b03e675fddc32ffd25ec7b` |
| extension48 hidden acceptance | `395e1651f52259de7e56a63476504891f136edd2d4dd5a8263064077741ede12` |
| post-run-only Codex references | `947a4b495951374b4d83a1029a2e3196e98c277e2c5d815919bdc58bf482d89b` |

正式 runner 还必须在 `Round13/` 中生成 runtime doctor、完整 source-tree manifest、
RUN_PROTOCOL、逐题 audit/model trace/event log/state timeline 和逐文件 workspace 摘要。任何生成后代码
变化都会使本轮失去冻结身份，不能混入结果。
