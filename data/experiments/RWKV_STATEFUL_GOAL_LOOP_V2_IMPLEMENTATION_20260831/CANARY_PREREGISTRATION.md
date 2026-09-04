# Stateful Goal Loop v2 固定 3 例 canary 预注册

- 登记时间：2026-08-31（Asia/Shanghai），在本轮任一 canary 模型请求前。
- suite：`agentladderv1`
- 固定顺序：`AGENT-LADDER-L1-FIX01`、`AGENT-LADDER-L4-LEDGER01`、`AGENT-LADDER-L5-RWKV01`。
- tasks SHA-256：`23cf009831fb38dd05bd3fad69e246a822a59ab6bd725833c6df2aaaf45c93bb`。
- hidden acceptance SHA-256：`f95da0b4085cdee3bc4555255dfb4f09d9272c00982634c72a040361c5774e06`。
- 输出目录：`data/experiments/RWKV_STATEFUL_GOAL_LOOP_V2_IMPLEMENTATION_20260831/run_stateful_goal_v2_s60_g3_g6_canary_v1`；运行前不存在，失败后不得覆盖。

## 冻结架构

- `rwkv-stateful-goal-loop.v2`。
- 一个 13.3B 权威 action State；2.9B selector 输出 Top-3；13.3B 在 Top-3 内选择 operation 并生成参数。
- 每个 action/事务结束后使用同 profile 的临时 13.3B Audit Fork；audit WKV 不合并，只有通过证据引用校验的结构化结论回写主 State。
- 强模型关闭；Supervisor request 必须为 0；atom pool 关闭；并行 mutation 关闭。
- 顶层 lifecycle=`goal`；max transitions 为每次 continuation slice 的 300，边界只 yield，不强制 Final。
- hidden acceptance 不进入 PlanPatch、Selector、Executor 或 Audit 输入。

## 冻结运行身份

- Executor：`rwkv7-g1i-13.3b-exe-g3-g6-deterministic-cmix-r7-multiprofile-ctx2496`，本地 endpoint `127.0.0.1:29613`。
- Executor native protocol：`rwkv-lh.native-state.v1`；create/resume/fork/commit/rollback/export/import 全部为 true；prompt replay=false。
- Selector：`rwkv7-g1i-2.9b-vllm-v1`，model SHA-256 `01f39dd59fc402fbe8ba49765a1997ee9dbc82427bf0ece6a4fac520e9eb8044`。
- Selector head SHA-256：`721669ce8733b590b3aa6c910d8bc13d744612f1fee884d5276a3f0d96d0d441`；head hash `205f995690232aef9c442b19a009fb2eda4c6be4e524e3fc903bb2dd17d72f9e`。
- Selector input protocol：`rwkv-lh.exact-tool-selector-input.v7-requirement-byte-tail`；profile=`zero`。
- 离线/联网 profile 仍由每个冻结 Goal 的 retrieval policy 一次绑定为 G3/G6，不在任务内切换。

## 冻结实现摘要

| 文件 | SHA-256 |
|---|---|
| `scripts/run_rwkv_e2e_benchmark.py` | `6d9f723ecc22033f2fbf8bbc3460e7d5e09ce9291a993b2034a7ae7dd53a461a` |
| `rwkv_lh/controller.py` | `0684634392ae1bd06f0b9c488142c5c410d5f7f0a0d80809faf7836f8ed6c66f` |
| `rwkv_lh/stateful_goal_loop.py` | `7119f7cb8203daefa32d466edada378317d9aad6046061f0c7d9bd823a7ee149` |
| `rwkv_lh/goal_loop_protocol.py` | `b3c5b076eb337792359480c8c56c6ecb731e69a1999645387885cb544277cd5b` |
| `rwkv_lh/model.py` | `b955ead7f3e97d28dc9cf4ac7b0f934999b26dd394267ef1bf89c97771af50c5` |
| `rwkv_lh/model_session.py` | `c6deda8f32c3f89d45824b4933aee6109c2fcc2493e13800cb8a925f70e27cd6` |
| `rwkv_lh/schema.py` | `967edc9fd0cdbf76e746df78d820438a7bd542859766c42ab38cd70f0417afc8` |
| `rwkv_lh/exact_tool_selector/network_protocol.py` | `634058bd80cb7f1669367b945672a8723bd2726b6965254746575e32ab60de28` |

## 固定命令

```bash
uv run python /home/chase/GitHub/RWKV-LH/scripts/run_rwkv_e2e_benchmark.py \
  --suite agentladderv1 \
  --case AGENT-LADDER-L1-FIX01 \
  --case AGENT-LADDER-L4-LEDGER01 \
  --case AGENT-LADDER-L5-RWKV01 \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/RWKV_STATEFUL_GOAL_LOOP_V2_IMPLEMENTATION_20260831/run_stateful_goal_v2_s60_g3_g6_canary_v1 \
  --max-transitions 300 \
  --concurrency 1 \
  --tool-disclosure-mode progressive \
  --independent-selector \
  --stateful-goal
```

## 判定

评价算法、hidden checker、任务与阈值沿用冻结 Agent Ladder。通过门槛不变：completed=`3/3`、external=`3/3`、strict=`3/3`。任一项未达到则 v2 能力门未通过，不运行完整 10 例，不通过修改任务、输出、checker、重试筛选或阈值补救。
