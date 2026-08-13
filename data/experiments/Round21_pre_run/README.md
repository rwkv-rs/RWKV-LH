# Round21 正式运行前冻结记录

记录日期：2026-08-13；以下实现和评价口径在任何 Round21 RWKV 请求之前冻结。

## 唯一变量

- 协议：`../Round21_PROTOCOL.md`，SHA-256
  `845b39e1f174e535b39f3e0863267e9c3f9c25c7b8adf81829e8dd53b5d131e3`。
- 变量：`transitive_model_written_snapshot_lineage.v1`。
- 当 RWKV 选择的 expected 是同一目标的只读 dependency snapshot，且审计时序能证明该 snapshot
  发生在较早的模型 mutation 之后，该 expected 继续归属于 model-written target lineage。
- 没有较早 mutation 的初始 snapshot、mutation 前 snapshot、不同 target、无可靠时序来源继续保留。
- proof engine 不生成 assertion、source、selector、transform、criterion 或值；不读取标准答案；不修改
  RWKV action、witness 决定和最终输出。

## 冻结回归

- 全产品测试：`239/239`，JUnit SHA-256
  `f5337b5fa0210da907848d94edf994add1f1432a08d5507372299850ca977822`。
- LH-Control 正式隔离复跑：`30/30`，结果位于 `lh_control_30_final/results.json`，SHA-256
  `16da8c4851ffe661cc48a27b3bd6d6efaab40b5d56947f98ce1e512a0981524d`。
- RWKV-E2E-90 validate-only：90 selected，`catalog_valid=true`。
- Round18 冻结 proof-pass 重放：13 条中 12 条由 model-written target lineage 拒绝，1 条由既有
  artifact hash 规则拒绝，0 条保留；SHA-256
  `4f03af1ddab124f80af6ce0fa085db5874f624e67c400ad365bfdeb4b70689f9`。
- Round19 obligation 重放：112 个 proposal 中 4 个命中 Round20 unchanged gate、涉及 3 题，
  历史追加任务 16 个；SHA-256
  `ba2d202a1a8602024ce953c0dfdd1c512a11906f4990c43ba0b027824655e5d3`。
- Round20 proof-pass 重放：11 条中 9 条传递性 model-written lineage 被拒绝、2 条无早期同目标
  mutation 的只读 snapshot 保留；`E2E-B02` 的 4 条全部拒绝；SHA-256
  `009b166c58b8d948fc3b00fbc2c3441ee2ab5df64555b80a7ca9a950d740528f`。

## 输出隔离诊断

首次正式 LH-Control 为 30/30。代码增加 symlink/parent-traversal fail-closed 测试后，曾错误复用原
`lh_control_30/` 输出目录再次运行；框架正确拒绝覆盖已有 state，得到 2/30 和 28 个
`stale state revision`/`FileExistsError`。该失败目录保留为输出隔离诊断，SHA-256
`35ef110299fab91add1e31f5002ef4cc715ec6e27b106433e0467afb5f6b5405`，不作为产品回归结果。
随后使用全新 `lh_control_30_final/` 目录复跑并得到上述 30/30。

## 冻结实现摘要

| 文件 | SHA-256 |
| --- | --- |
| `rwkv_lh/proof.py` | `1814439ccc471731624e3fd140ece830dcfef62554a1846fadf5849019eda8d9` |
| `rwkv_lh/controller.py` | `a7d2267d29d85eb546733ecfa654e052469c0d42571ea06d36dc817dcce3ec55` |
| `rwkv_lh/model.py` | `75d71361cfd32a31d28df917b67597ec8da2e310296e045134c1d27c2f7fd973` |
| `tests/test_criterion_proof.py` | `af811473aaf3fb7689bdd061011f1d4d080544405dcf13e78a5acb7a81bd35b1` |
| `tests/test_long_horizon_controller.py` | `eb36f742050a8d847c16731a7d87b2a9fea419d477e5f98828f5bbb1aa9aa2ec` |
| `temp/replay_round20_proof_passes_with_round21.py` | `dd8369583b0bb7882506dd6aa4e8bd1da61b5bbb7ee3f9b39abbe171a07ccf32` |

## 正式运行环境

- endpoint：`http://127.0.0.1:29610/v1`；
- 模型：`rwkv7-g1i-13.3b-20260805-ctx16384`；max model length `16384`；
- 固定数据集：RWKV-E2E-90，Basic/Medium/Hard 各 30；
- 使用既有 Round20 runner 参数、采样参数、并发与最大 transition；
- hidden acceptance/reference 在 90 题终止前禁止读取；runner 必须生成 runtime doctor、完整
  source-tree manifest、RUN_PROTOCOL 和 90 题全量审计。
