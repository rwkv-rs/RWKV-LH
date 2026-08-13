# Round23 正式运行前冻结记录

冻结日期：2026-08-13。以下协议、实现、冻结回放、数据集、运行参数和评价门禁均在任何Round23 RWKV请求之前确定。没有读取Round23 hidden acceptance、standard answer或Codex reference。

## 1. 唯一结构变量

- 预注册协议：[`../Round23_PROTOCOL.md`](../Round23_PROTOCOL.md)，SHA-256 `91c1a7154895c27226c914336289c6790774e11d36d7411bd512a74f0fbe038b`。
- 变量：`transparent_protocol_boundary_closure.v1`。
- 只闭环预注册的唯一Plan task-array和selected single-action wire envelope，并把第一次Plan/action parser或normalizer错误放回原有同类型两次纠错循环。
- raw payload与canonical view分开保存；每次归一化记录transform list、normalizer version、raw/normalized digest和`controller_semantic_fields_generated=false`。
- 不修改Goal、Task语义、dependency、criterion、priority、action选择、argument、值、代码、final output、proof、completion、recovery、Harness或评分。
- 首版预注册在运行前冻结raw检查时发现M09的单项`tool_calls`为直接`name/arguments`，与H07的嵌套`function`不同；协议正文已在任何Round23请求前以显式勘误登记两种精确wire variant。没有根据答案或参数正确性选择接受。

此前的workspace-observation单点候选已在运行前中止，原文保存在
[`../Round23_ABORTED_PROTOCOL_DISJOINT_OBSERVATION.md`](../Round23_ABORTED_PROTOCOL_DISJOINT_OBSERVATION.md)，没有覆盖或删除失败的结构判断记录。

## 2. 实现文件

| 文件 | SHA-256 |
|---|---|
| `rwkv_lh/tool_protocol.py` | `bc236aa06ff3755f675651b63c1b336a3a6e90082a2776f5093319bbdea4a6e6` |
| `rwkv_lh/model.py` | `2a357e74ce11cd6c0422179e322b60dd869a16228c7939622ff39af14016e563` |
| `tests/test_tool_protocol.py` | `01ccc79ecf45829e9adf8b2ab8ca427701019f565f7f9124a3cde532cb9bac76` |
| `tests/test_long_horizon_controller.py` | `6424ab9e8ed95fb3c7d3181b3725d6b329fe68c94732a48b3611ee98d1fb145b` |
| `temp/replay_round22_protocol_boundary_v1.py` | `6519021c39c2b65ddcaa89a9d9b18f24b2053a750f8b839e1a6c67c3ee88da37` |

该工作树包含Round22及更早轮次尚未统一提交的历史实现；上表哈希冻结的是正式Round23实际运行代码整体，不把本轮局部diff错误表述成整个文件都由Round23新建。

## 3. 单元、对抗与全产品测试

- Round23相关protocol/controller定向测试：`79/79`。
- 全产品pytest：`272/272`；JUnit `pytest.xml` SHA-256
  `7d2bb2755b644e7dde3a44ee86a31acf4bb61a570aa23336cf1df1c9fdff9141`。
- 新测试覆盖：四类新增single-action envelope、两类single `tool_calls`、selected identity绑定、JSON-string arguments、Plan task_graph schema闭环、冲突/多候选/参数越层/bare Task/truncated等失败关闭，以及第一次parser error真实触发同类型第二次request。
- `git diff --check`对本轮代码、协议和pre-run文档无错误。

## 4. Round22全量冻结协议回放

输出：[`ROUND22_PROTOCOL_BOUNDARY_REPLAY.md`](ROUND22_PROTOCOL_BOUNDARY_REPLAY.md)及
`round22_protocol_boundary_replay.json`，JSON SHA-256
`29bcbb12d67f99ce37090d740172619211abbce40122c7589a1bc3d4dd99bf4c`。

- 不调用RWKV、不执行Harness、不读取答案；读取Round22 `90/90` frozen model trace、event log和state timeline。
- 共复放`672`个Plan/action response，涉及`84`题；其余6题没有到达这两种request，但trace仍计入来源清单和hash。
- 每个新canonical payload继续通过当前TaskGraph、Goal binding或Harness action contract，不以normalizer接受代替真实校验。
- 旧protocol/contract error中`15`个request可继续，其中包含H02/LH07四个缺version的完整Plan以及11个唯一selected action外壳。
- accepted source identity/arguments/task array未原样保留：`0`；semantic mutation：`0`。
- H07绝对`cwd=/workspace`、B22绝对path、H05额外content、H16参数越层、M30/LH08 `model_action`身份冲突等继续失败关闭。

## 5. 历史状态与防作弊回归

| 回放 | 冻结结果 | SHA-256 |
|---|---|---|
| Round18 proof-pass | `13/13`同源/变更proof继续拒绝 | `4f03af1ddab124f80af6ce0fa085db5874f624e67c400ad365bfdeb4b70689f9` |
| Round19 obligation | `112`个proposal中`4`个继续被unchanged gate抑制 | `ba2d202a1a8602024ce953c0dfdd1c512a11906f4990c43ba0b027824655e5d3` |
| Round20 proof-pass | `9`条传递性同源拒绝，`2`条只读独立来源保留 | `009b166c58b8d948fc3b00fbc2c3441ee2ab5df64555b80a7ca9a950d740528f` |
| Round21 state chain | `26/26` artifact hash/size复现，`26/26` snapshot建立，`24/26`直接依赖可见 | `8f7eb836908fed0efaf4c03482dae73087a60ed3b5cd628ecf38c87c0b3e3ffe` |

LH-Control隔离正式运行：`30/30`；最终`lh_control_30_final/results.json` SHA-256
`8967e57fd289ae6e30fae740da1be325c238de6e88befb99f45321c7607344f8`。

E2E validate-only：`90` selected，`catalog_valid=true`。

## 6. 固定数据集和runner

| 文件 | 用途 | SHA-256 |
|---|---|---|
| `benchmarks/rwkv_e2e/rwkv_e2e_30/tasks.json` | Basic 30 | `0bf73c9a86bd014f5a94e5686ffe744bbef6c560f4227e37d0b753b900481c4c` |
| `benchmarks/rwkv_e2e/rwkv_e2e_extension48/tasks.json` | Medium 30 + Hard 18 | `384d52b5395dbcb31947dbfd1cfe63167ccbe68ed8b03e675fddc32ffd25ec7b` |
| `benchmarks/rwkv_e2e/rwkv_e2e_lh12/tasks.json` | Hard LH12 | `d813a7bc3a42e27ee3573ea342a918bd7ee5347ca8b0e893c04fded262457a5e` |
| `benchmarks/architecture_regression/lh_control_30/tasks.json` | 确定性架构回归 | `0606877c66360aefbf243b848a19fb349927e7a32e86565dbdc58e41ddcfbe80` |
| `scripts/run_rwkv_e2e_benchmark.py` | E2E runner | `c1d5c72550788c53826ab8a332c7a2ab6265a2353d236b2442a7c6a7a9ba47a8` |
| `scripts/run_lh_control_benchmark.py` | LH-Control runner | `85025858869d1503a025b7be1c4cbf9e2f1b8cc4c6b4138aaf018d57e138d201` |

## 7. 冻结runtime与正式运行参数

- endpoint：`http://127.0.0.1:29610/v1`；Authorization：既有本地Bearer配置。
- endpoint在冻结时返回模型`rwkv7-g1i-13.3b-20260805-ctx16384`，`max_model_len=16384`，root为本地RWKV权重；没有其他model。
- suite=`all`；Basic/Medium/Hard各30；`max-transitions=200`；`concurrency=8`；采样、stop、timeout沿用Round22代码与runtime配置。
- 正式输出固定为`data/experiments/Round23/`。
- 90题全部终止前不读取acceptance、standard answer或reference；先冻结model trace、events、state、artifacts与score-independent analysis，再解封评分。

## 8. 冻结评价与GitHub门禁

首要看注册外壳、局部纠错、first Task/Harness/producer reachability及其真实producer质量，同时报告External、Strict、Completed、FP/FN、难度、请求/attempt、side effect和evidence漏斗。

GitHub只在以下条件全部满足时晋级：FP=`0`、semantic mutation=`0`、全回归通过；External不低于Round16的`24`、Strict/Completed不低于`0`；并且External `>24`、Strict `>0`或Completed `>0`至少一项严格改善。运行后不得修改门禁、白名单或评分口径。
