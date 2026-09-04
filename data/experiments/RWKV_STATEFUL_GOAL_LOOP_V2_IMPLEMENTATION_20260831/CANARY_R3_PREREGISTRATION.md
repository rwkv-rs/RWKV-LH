# Stateful Goal Loop v2 Strong Planner canary R3 预注册

- 登记时间：2026-09-01T00:05+08:00，早于本轮任何 Ladder task model 请求。
- 继承固定 suite/order：`agentladderv1`；`AGENT-LADDER-L1-FIX01`、`AGENT-LADDER-L4-LEDGER01`、`AGENT-LADDER-L5-RWKV01`。
- tasks SHA-256：`23cf009831fb38dd05bd3fad69e246a822a59ab6bd725833c6df2aaaf45c93bb`。
- acceptance SHA-256：`f95da0b4085cdee3bc4555255dfb4f09d9272c00982634c72a040361c5774e06`。
- R2 原始 `0/3`、输出和 Planner cache 保持不可覆盖；R2 根因见 `CANARY_R2_ANALYSIS.md`。
- R3 输出目录与 cache 在预注册时均不存在。

## R2 后唯一整改变量

1. Strong Planner、`ContractGraphPatch`、case、阈值、Strong/13.3B/2.9B 模型身份、sampling 和 transition budget 均不变。
2. 13.3B Top-K operation choice 改为接受模型在冻结候选内明确生成的实际 operation 名；schema 公开前的参数被记录并丢弃，随后只公开被选 schema 并重新生成参数。choice candidate 不授权 action，其 WKV 不 merge，只追加验证后的有界 delta。
3. Audit Fork 公开唯一 `audit_decision` schema；模型只生成 `verdict/step_id/step_complete/evidence_refs/gaps/reason`，kernel 绑定 audit id/schema version 并限制证据投影。
4. benchmark 的 Stateful action/protocol rejection 统计直接读取唯一主 State，不再误读空 parallel outcomes。该改动只修 observability，不改变 pass 判定。
5. 不新增 RWKV PlanPatch，不调用 Strong Reviewer，不启用 atom worker pool。

## 冻结运行身份

- Strong Planner readiness：OpenAI-compatible `gpt-5.4-mini` 可用，reasoning effort=`none`，temperature=`0.1`，semantic repair attempts=`2`。
- Planner cache：新的空目录 `data/experiments/RWKV_STATEFUL_GOAL_LOOP_V2_IMPLEMENTATION_20260831/supervisor_plan_cache_canary_r3`。
- Executor：`rwkv7-g1i-13.3b-exe-g3-g6-deterministic-cmix-r7-multiprofile-ctx2496`，`127.0.0.1:29613`。
- Native protocol：`rwkv-lh.native-state.v1`，create/resume/fork/commit/rollback/export/import 全部 true，prompt replay=false。
- Selector：`rwkv7-g1i-2.9b-vllm-v1`；model SHA-256 `01f39dd59fc402fbe8ba49765a1997ee9dbc82427bf0ece6a4fac520e9eb8044`。
- Selector head SHA-256：`721669ce8733b590b3aa6c910d8bc13d744612f1fee884d5276a3f0d96d0d441`；head hash `205f995690232aef9c442b19a009fb2eda4c6be4e524e3fc903bb2dd17d72f9e`；input v7 requirement-byte-tail；profile=`zero`。
- 输出目录：`data/experiments/RWKV_STATEFUL_GOAL_LOOP_V2_IMPLEMENTATION_20260831/run_stateful_goal_v2_strong_planner_s60_g3_g6_canary_r3`。

## 冻结回归

- 相关路径：`117 passed in 26.15s`；benchmark/Stateful 后续定向：`41 passed in 11.27s`。
- 最终全量：`752 passed, 1 warning in 153.72s`。
- 唯一 warning：Python 3.13 multiprocessing 多线程 `fork()` deprecation，非本轮新增。

| 文件 | SHA-256 |
|---|---|
| `rwkv_lh/controller.py` | `c239ac927b08d723e692add9aa2e09dab9941eb3e8abcee43e4a7d7d0e9c0398` |
| `rwkv_lh/stateful_goal_loop.py` | `df279fdc965efdefa802e040c2b10fed9512ebe7d4c4cedd0f672693e1679bde` |
| `rwkv_lh/goal_loop_protocol.py` | `3aed23f4dc3857c446ea45d91ef016b8ff8edddccc1cc09589dba93d6cdd5884` |
| `rwkv_lh/model.py` | `52295b65d46ade4efd97e8f5252869e0bd4d98b4abcca4fda57ab760bb18c90e` |
| `rwkv_lh/model_io.py` | `a83740ad002940bbf27e9840de5d2aebe07546d375bea1673c192a959799bad5` |
| `rwkv_lh/model_session.py` | `5f27a6c0ecefaaf21248c6615d70818197a1e66e18ca699507c2c803ac2fa18e` |
| `rwkv_lh/product_runtime.py` | `cc48332cdecbeaab47d2e4b7fac2fa6d3d13abd5ae195258d6f5f7abb9c2497d` |
| `rwkv_lh/schema.py` | `51116b6be1114f60f0e9258aaede19218c1c27ebf1da62c43a865437f57e9a3f` |
| `rwkv_lh/exact_tool_selector/network_protocol.py` | `634058bd80cb7f1669367b945672a8723bd2726b6965254746575e32ab60de28` |
| `scripts/run_rwkv_e2e_benchmark.py` | `b1fd6726724b3955b2c1b509712c8643b314e2facc397f0ca30287f65e555ef2` |
| `tests/test_stateful_goal_loop.py` | `303c1c8aa9fadd89564df032cfbd4d71dce48ef68abfdea99980b5f6a8c97d4c` |
| `tests/test_model_session.py` | `23194c24f2b8335330cd47e2b184ab4a946c275a6572154d798647b12ae9a711` |
| `tests/test_independent_network_selector_integration.py` | `96d7573df638867034286e515af921f790173ebb4406ec7a6080a05b4922b7ff` |
| correction manifest | `dea655a20f7e1fcaeab19bda9afa5f26816b241b04a4ec2b873a320ddaeceb89` |

## 固定命令

```bash
SUPERVISOR_PLAN_CACHE_DIR=/home/chase/GitHub/RWKV-LH/data/experiments/RWKV_STATEFUL_GOAL_LOOP_V2_IMPLEMENTATION_20260831/supervisor_plan_cache_canary_r3 \
uv run python /home/chase/GitHub/RWKV-LH/scripts/run_rwkv_e2e_benchmark.py \
  --suite agentladderv1 \
  --case AGENT-LADDER-L1-FIX01 \
  --case AGENT-LADDER-L4-LEDGER01 \
  --case AGENT-LADDER-L5-RWKV01 \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/RWKV_STATEFUL_GOAL_LOOP_V2_IMPLEMENTATION_20260831/run_stateful_goal_v2_strong_planner_s60_g3_g6_canary_r3 \
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

- 能力门：completed/external/strict 同时 `3/3`；否则不运行完整 Ladder。
- 架构门：每例 patch≥1；RWKV GoalPlanPatch、atom outcome、Strong review=0；只有一个权威 13.3B action State；Audit fork 存在且 WKV merge=0。
- Strong trace phase 只能是 `contract_plan`。
- 报告必须同时给出 results summary 与 causal ledger action/rejection/audit 计数；二者不一致即 observability gate 失败。
- 不在运行后修改 task、acceptance、阈值、重试筛选、相似度、源码或输出。
