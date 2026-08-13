# Round22 正式运行前冻结记录

记录日期：2026-08-13。以下实现、数据集、回放结果和评价门禁在任何 Round22 RWKV 请求之前冻结。

## 唯一结构变量

- 协议：`../Round22_PROTOCOL.md`，SHA-256
  `e33fc766b5cfe900416b1ce0879975049671f098bacf20d9f3f79591502a5220`。
- 变量：`post_action_workspace_snapshot_memory.v1`。
- 对 Harness 成功执行的 `write_file`、`write_json`、`append_file`、`copy_file`，控制器从真实
  post-action workspace path 重新读取 artifact；仅当 scope、symlink、size 和 SHA-256 检查通过时，
  创建独立、append-only 的 observation memory。
- 原 `action_result` memory 和 RWKV action output 保持不变；后继 action、值、覆盖、completion 与
  final output 仍由 RWKV 决定。snapshot 不读取 acceptance/reference/standard answer，不生成任务、
  criterion、assertion、expected 或答案。
- 内容上限为 20,000 bytes。超限或非 UTF-8 只保留真实 metadata；scope、symlink、hash/size 异常时
  不创建 snapshot，并记录失败关闭的 audit event。
- snapshot 只通过 producer task 的依赖投影进入上下文；非依赖任务即使显式写入 snapshot memory ID
  也不会获得该内容。

## 实现与边界测试

| 文件 | SHA-256 |
| --- | --- |
| `rwkv_lh/controller.py` | `dcb005d3e8fcd816976d0ef167ff6b98ee9ea9ba5dccf4e64de8950d239bbb1d` |
| `rwkv_lh/memory.py` | `5e9db851403cb4ab6db0cc3729524cb76007fc080639723069a715614f8116dc` |
| `tests/test_post_action_workspace_snapshot.py` | `87c8909b4a83cee39ad6e57b26a37b70bd807004b7efc477e8f154f269aec89f` |
| `temp/replay_round21_state_chains_with_round22.py` | `4567f87edef3c0cfeb9a83e6e0416e28bc710a65eb9dd50a6f21f640feed51ac` |

新增 13 个测试覆盖四类 mutation、原回执不变、真实 bytes/hash、直接依赖投影、非依赖隔离、失败
action、read-only action、hash/size mismatch、20,000-byte 边界、非 UTF-8、symlink、父目录 traversal、
绝对路径、审计事件以及 state save/load。

## 冻结回归

- 全产品测试：`252/252`；JUnit `pytest.xml` SHA-256
  `67b0ebc22ad6956e0909a2b60af7bd12951badb79190962e618c8b082956eb90`。
- LH-Control 正式隔离运行：`30/30`；`lh_control_30/results.json` SHA-256
  `15fe820036a5d6e4883f54cbf6e5b08cd880d6a0535996d13330a6a007f53926`。
- RWKV-E2E-90 validate-only：`90` selected，`catalog_valid=true`。
- Round18 proof-pass 回放：`13/13` 继续拒绝；SHA-256
  `4f03af1ddab124f80af6ce0fa085db5874f624e67c400ad365bfdeb4b70689f9`。
- Round19 obligation 回放：112 个 proposal 中 4 个继续被 unchanged gate 抑制，涉及 3 题；SHA-256
  `ba2d202a1a8602024ce953c0dfdd1c512a11906f4990c43ba0b027824655e5d3`。
- Round20 proof-pass 回放：11 条中 9 条传递性 lineage 拒绝、2 条只读来源保留；SHA-256
  `009b166c58b8d948fc3b00fbc2c3441ee2ab5df64555b80a7ca9a950d740528f`。

## Round21 冻结状态链盲态回放

- 输出：`round21_state_chain_replay.json`，SHA-256
  `d2f2424f7cd0a26ab86b854c43795ad0c2e2ff7543b17d682d6ee72888750822`。
- 来源：Round21 冻结 `state_transfer_analysis.json`、14 题的 public `event_log.json` 与
  `state_timeline.json`。输出 JSON 内逐文件记录路径和 SHA-256。
- 生成方式：从 `attempt_started` 恢复 26 个 prior mutation 的原 action 参数，用当前 Harness 在隔离
  临时 workspace 确定性重放，再通过当前 `_record_artifacts_and_memory` 和
  `WorkingMemoryBuilder` 投影；没有读取 `results.json`、acceptance、reference、standard answer、
  `.verifier-private` 或 post-standard attribution。
- 26/26 historical artifact hash 与 size 完全复现；26/26 创建 exact post-action snapshot。
- 24/26 后继任务直接依赖 producer，因此 exact snapshot 进入后继 context。
- 2/26（B28 T2→T6、H08 T3→T5）只有跨层传递依赖；现有 builder 只投影直接依赖，本轮不跨中间任务
  传播。这是预先记录的能力边界，不在正式运行后改变量。

## 固定数据集

| 数据集 | 版本/用途 | SHA-256 |
| --- | --- | --- |
| `benchmarks/rwkv_e2e/rwkv_e2e_30/tasks.json` | RWKV-E2E core30，Basic 30 | `0bf73c9a86bd014f5a94e5686ffe744bbef6c560f4227e37d0b753b900481c4c` |
| `benchmarks/rwkv_e2e/rwkv_e2e_lh12/tasks.json` | RWKV-E2E lh12，Hard 12 | `d813a7bc3a42e27ee3573ea342a918bd7ee5347ca8b0e893c04fded262457a5e` |
| `benchmarks/rwkv_e2e/rwkv_e2e_extension48/tasks.json` | RWKV-E2E extension48，Medium 30 + Hard 18 | `384d52b5395dbcb31947dbfd1cfe63167ccbe68ed8b03e675fddc32ffd25ec7b` |
| `benchmarks/architecture_regression/lh_control_30/tasks.json` | LH-Control-30 deterministic architecture regression | `0606877c66360aefbf243b848a19fb349927e7a32e86565dbdc58e41ddcfbe80` |

E2E runner SHA-256 为
`c1d5c72550788c53826ab8a332c7a2ab6265a2353d236b2442a7c6a7a9ba47a8`；LH-Control runner SHA-256 为
`85025858869d1503a025b7be1c4cbf9e2f1b8cc4c6b4138aaf018d57e138d201`。

## 正式实验与上传门禁

- endpoint：`http://127.0.0.1:29610/v1`；模型：
  `rwkv7-g1i-13.3b-20260805-ctx16384`；context `16384`。
- RWKV-E2E-90：Basic/Medium/Hard 各 30；并发 8；最大 transitions 200；采样与 Round21 相同。
- 90 题全部终止前不加载 hidden acceptance/reference；先冻结 raw/normalized payload、event、state
  timeline、artifact 与 snapshot audit，先做盲态因果分析，再解封标准答案评分。
- GitHub 门禁保持预注册值：FP=0、Strict>7、Completed>7、External>=24、全部回归通过且 output
  non-intervention 成立；正式运行后不修改。
