# Stateful Goal Loop v2 Strong Planner canary R2 预注册

- 登记时间：2026-08-31（Asia/Shanghai），早于本轮任何任务模型请求。
- 前置只读探测：Strong Planner readiness 已执行一次无任务内容的 models/chat probe；未发送 Ladder 请求、workspace 或 acceptance。
- 勘误依据：`ARCHITECTURE_CORRECTION_ADDENDUM.md`。R1 的关闭 Planner 拓扑无效且保持不可覆盖。
- suite 与固定顺序：`agentladderv1`；`AGENT-LADDER-L1-FIX01`、`AGENT-LADDER-L4-LEDGER01`、`AGENT-LADDER-L5-RWKV01`。
- tasks SHA-256：`23cf009831fb38dd05bd3fad69e246a822a59ab6bd725833c6df2aaaf45c93bb`。
- hidden acceptance SHA-256：`f95da0b4085cdee3bc4555255dfb4f09d9272c00982634c72a040361c5774e06`。
- 输出目录：`data/experiments/RWKV_STATEFUL_GOAL_LOOP_V2_IMPLEMENTATION_20260831/run_stateful_goal_v2_strong_planner_s60_g3_g6_canary_r2`；运行前必须不存在，失败后不得覆盖。

## 冻结架构

1. Strong Model 仅调用现有 `plan_contract_graph()`，唯一计划格式为已验证的 `ContractGraphPatch`；不得调用 Strong Reviewer。
2. Strong work nodes 串行投影到一条 13.3B action State；atom worker pool、独立 atom WKV 与旧 RWKV finalizer 均关闭。
3. 2.9B Selector 在当前 Strong Planner frontier allowset 内返回 Top-3 与原始 logits；13.3B 选择 operation 并生成参数。
4. 每个 ActionResult 在同一主 State 上追加，固定边界 fork 同 profile 13.3B Audit；Audit WKV 永不合并。
5. RWKV Audit 可输出 `continue|repair|ready_for_final`；Evidence Kernel 只能否决未知证据、越界 step 或伪完成。
6. `repair` 经过确定性投影后只作为 Strong Planner correction 输入；Controller 不生成 obligation verdict 语义，不调用 Strong Reviewer。
7. 只有原始 13.3B `final_answer` 且 pre-final Audit 为 `ready_for_final` 才能 `run_completed`。

## 冻结运行身份

- Strong Planner：OpenAI-compatible `gpt-5.4-mini`，reasoning effort=`none`，temperature=`0.1`，semantic repair attempts=`2`。
- Planner cache：为本轮设置新的空目录 `data/experiments/RWKV_STATEFUL_GOAL_LOOP_V2_IMPLEMENTATION_20260831/supervisor_plan_cache_canary_r2`，不得读取历史 Ladder planner cache。
- Executor：`rwkv7-g1i-13.3b-exe-g3-g6-deterministic-cmix-r7-multiprofile-ctx2496`，endpoint `127.0.0.1:29613`。
- Executor native protocol：`rwkv-lh.native-state.v1`，create/resume/fork/commit/rollback/export/import 全部为 true，prompt replay=false。
- Selector：`rwkv7-g1i-2.9b-vllm-v1`，model SHA-256 `01f39dd59fc402fbe8ba49765a1997ee9dbc82427bf0ece6a4fac520e9eb8044`。
- Selector head SHA-256：`721669ce8733b590b3aa6c910d8bc13d744612f1fee884d5276a3f0d96d0d441`；head hash `205f995690232aef9c442b19a009fb2eda4c6be4e524e3fc903bb2dd17d72f9e`。
- Selector input：`rwkv-lh.exact-tool-selector-input.v7-requirement-byte-tail`；profile=`zero`。

## 冻结实现与回归

- 全量回归：`750 passed, 1 warning in 160.31s`，命令 `uv run pytest -s -q`。
- 唯一 warning：Python 3.13 multiprocessing fork deprecation，实施前已存在。

| 文件 | SHA-256 |
|---|---|
| `rwkv_lh/controller.py` | `c239ac927b08d723e692add9aa2e09dab9941eb3e8abcee43e4a7d7d0e9c0398` |
| `rwkv_lh/stateful_goal_loop.py` | `583996ee4579ed79184cf12d8ef624cb371dd3e708177a580139b31853dd0604` |
| `rwkv_lh/goal_loop_protocol.py` | `aaf30227c97be4227034748cd93466c3fbce0ec355b28e41cc8054dbe4825b68` |
| `rwkv_lh/model.py` | `8254916d2e56b755f4186601e771d66bcc54c708005d444bd414e25b4982a294` |
| `rwkv_lh/model_session.py` | `5f27a6c0ecefaaf21248c6615d70818197a1e66e18ca699507c2c803ac2fa18e` |
| `rwkv_lh/product_runtime.py` | `cc48332cdecbeaab47d2e4b7fac2fa6d3d13abd5ae195258d6f5f7abb9c2497d` |
| `rwkv_lh/schema.py` | `51116b6be1114f60f0e9258aaede19218c1c27ebf1da62c43a865437f57e9a3f` |
| `rwkv_lh/exact_tool_selector/network_protocol.py` | `634058bd80cb7f1669367b945672a8723bd2726b6965254746575e32ab60de28` |
| `scripts/run_rwkv_e2e_benchmark.py` | `491b62e3c1de836ccac90c362234d6b04d2d46e84a1ccc7231b2251a161c2b90` |
| `tests/test_stateful_goal_loop.py` | `be20b4594424f12a6a2431d165ef0aefa094b93dc09934e436c0f80002e8c87e` |

## 固定命令

```bash
SUPERVISOR_PLAN_CACHE_DIR=/home/chase/GitHub/RWKV-LH/data/experiments/RWKV_STATEFUL_GOAL_LOOP_V2_IMPLEMENTATION_20260831/supervisor_plan_cache_canary_r2 \
uv run python /home/chase/GitHub/RWKV-LH/scripts/run_rwkv_e2e_benchmark.py \
  --suite agentladderv1 \
  --case AGENT-LADDER-L1-FIX01 \
  --case AGENT-LADDER-L4-LEDGER01 \
  --case AGENT-LADDER-L5-RWKV01 \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/RWKV_STATEFUL_GOAL_LOOP_V2_IMPLEMENTATION_20260831/run_stateful_goal_v2_strong_planner_s60_g3_g6_canary_r2 \
  --max-transitions 300 \
  --concurrency 1 \
  --tool-disclosure-mode progressive \
  --independent-selector \
  --supervisor openai \
  --supervisor-strategy contract_graph \
  --supervisor-pending-resume-attempts 2 \
  --stateful-goal
```

## 固定判定

- 能力门：completed/external/strict 必须同时达到 `3/3`；否则不运行完整 Ladder。
- 架构门：每例至少一个 `contract_graph_patch_committed`；`goal_plan_patch_*`、`atom_outcome_committed`、`contract_graph_review_committed` 必须均为 0；审核 fork 必须存在且 audit WKV merge 为 0。
- Strong 调用只能是 `contract_plan`；任何 `contract_review` 或 final presentation review 调用均判架构门失败。
- 任务、hidden checker、阈值、重试筛选、相似度和输出不得在运行后修改。

