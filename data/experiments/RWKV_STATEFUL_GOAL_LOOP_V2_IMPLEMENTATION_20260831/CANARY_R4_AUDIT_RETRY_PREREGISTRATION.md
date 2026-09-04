# Stateful Goal Loop v2 Audit 原地纠错 canary R4 预注册

- 登记时间：2026-09-01T00:33:49+08:00，早于本轮任何 Ladder task model 请求。
- 目的：只隔离验证 R3 唯一主阻塞——RWKV Audit 在同一 action/observation 边界内能否依据确定性错误反馈自行纠正；不重新评价 Strong Planner，不把本轮解释为能力通过。
- 固定 suite/case：`agentladderv1` / `AGENT-LADDER-L4-LEDGER01`。
- tasks SHA-256：`23cf009831fb38dd05bd3fad69e246a822a59ab6bd725833c6df2aaaf45c93bb`。
- acceptance SHA-256：`f95da0b4085cdee3bc4555255dfb4f09d9272c00982634c72a040361c5774e06`。
- R3 原始 `0/3`、输出和 causal ledger 保持不可覆盖；R3 中 Audit 为 `0/16` accepted。
- R4 输出目录在预注册时不存在。

## 唯一整改变量

1. Strong Planner、`ContractGraphPatch`、固定 L4 case、模型身份、sampling、Top-K operation choice、tool schema disclosure、transition budget 和判定口径不变。
2. Audit validation 失败后不再推进到下一次 tool choice；在同一 action/observation、同一 evidence projection 上最多进行 3 次 Audit 尝试。
3. 每次尝试都从当前主 State checkpoint 创建新的同 profile 13.3B Audit fork；candidate WKV 全部 rollback，永不 merge。
4. 失败尝试只向主 State 追加确定性的有界 `goal_audit_retry_feedback`，包含协议/语义/evidence kernel 的实际拒绝原因；成功后只追加 kernel 验证过的 audit delta。
5. 不修改 Strong Planner patch，不新增 RWKV PlanPatch，不调用 Strong Reviewer，不启用 atom worker pool。

## 冻结 Planner 与运行身份

- 直接复用 R3 的 Strong Planner cache；预期本轮 Strong HTTP 请求为 0。若 cache 文件集合或哈希改变，则 frozen-planner gate 失败。
- Planner cache：`data/experiments/RWKV_STATEFUL_GOAL_LOOP_V2_IMPLEMENTATION_20260831/supervisor_plan_cache_canary_r3`。
- cache 文件 SHA-256：
  - `14d236224aec4aa454700b54c17ab4a5c4927b4be6731b3727968915a74456f8.json`：`5043cc0063fe83356c723248175d7db1b59c58cf47e516423586732bd4bd28e6`
  - `2404b5b51c5e881bff9412cc3835e0b9590c9be0d2edf9c5dec322b1ada199a2.json`：`8221685335c086a501e1c6827ebd552ca72e89b4480463987f826eed512a8778`
  - `acf3a7861d61a7bc2ec9a719947d0c110816a0c563314de5dd5750e79c42b8fb.json`：`93cc274bbe17415e51831c852c8ce8e0fef685a2e0ca80bf78b378de15305cd6`
- Executor：`rwkv7-g1i-13.3b-exe-g3-g6-deterministic-cmix-r7-multiprofile-ctx2496`，`127.0.0.1:29613`。
- Native State protocol：create/resume/fork/commit/rollback/export/import 全部 true，prompt replay=false。
- Selector：`rwkv7-g1i-2.9b-vllm-v1`；model SHA-256 `01f39dd59fc402fbe8ba49765a1997ee9dbc82427bf0ece6a4fac520e9eb8044`。
- Selector head SHA-256：`721669ce8733b590b3aa6c910d8bc13d744612f1fee884d5276a3f0d96d0d441`；head hash `205f995690232aef9c442b19a009fb2eda4c6be4e524e3fc903bb2dd17d72f9e`；input v7 requirement-byte-tail；profile=`zero`。
- 输出目录：`data/experiments/RWKV_STATEFUL_GOAL_LOOP_V2_IMPLEMENTATION_20260831/run_stateful_goal_v2_strong_planner_l4_audit_retry_canary_r4`。

## 冻结代码、数据与回归

- 相关路径：`147 passed in 38.26s`。
- 最终全量：`753 passed, 1 warning in 157.29s`。
- 唯一 warning：Python 3.13 multiprocessing 多线程 `fork()` deprecation，非本轮新增。

| 文件 | SHA-256 |
|---|---|
| `rwkv_lh/model.py` | `38a9f8ef9a519900d4b57940a53d7de3b7eebfd13a2368799caadc1ec994de56` |
| `rwkv_lh/goal_loop_protocol.py` | `3aed23f4dc3857c446ea45d91ef016b8ff8edddccc1cc09589dba93d6cdd5884` |
| `rwkv_lh/stateful_goal_loop.py` | `df279fdc965efdefa802e040c2b10fed9512ebe7d4c4cedd0f672693e1679bde` |
| `tests/test_stateful_goal_loop.py` | `651d5d020118f8110b80e40557f902e66ba5288f154239fe626d3d22ac5bcf72` |
| `scripts/run_rwkv_e2e_benchmark.py` | `b1fd6726724b3955b2c1b509712c8643b314e2facc397f0ca30287f65e555ef2` |
| correction manifest | `70a0a130fe9877636653bbaeac05120af253b9d7fa30398a7cb7ae8ce70f1dc3` |

## 固定命令

```bash
SUPERVISOR_PLAN_CACHE_DIR=/home/chase/GitHub/RWKV-LH/data/experiments/RWKV_STATEFUL_GOAL_LOOP_V2_IMPLEMENTATION_20260831/supervisor_plan_cache_canary_r3 \
uv run python /home/chase/GitHub/RWKV-LH/scripts/run_rwkv_e2e_benchmark.py \
  --suite agentladderv1 \
  --case AGENT-LADDER-L4-LEDGER01 \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/RWKV_STATEFUL_GOAL_LOOP_V2_IMPLEMENTATION_20260831/run_stateful_goal_v2_strong_planner_l4_audit_retry_canary_r4 \
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

- 本轮结构成功门：`goal_audit_accepted >= 1`；至少出现一次真实失败后的 `goal_audit_retry_feedback`；Audit fork WKV merge=`0`。
- frozen-planner gate：Strong patch 与 R3 对应 L4 cache 内容相同；cache 文件集合和 SHA-256 不变；Strong review=`0`；Strong trace phase 只能是 `contract_plan`。
- 权限门：只有主 13.3B action State 可执行 action；operation choice 与 Audit candidate 均不具 action authority。
- 即使结构门通过，也不把 L4 的 completed/external/strict 失败改写为成功，不运行完整 Ladder。
- 若结构门失败，停止继续 live canary，把失败 Audit→正确 Audit 纳入 13.3B state-tuning correction corpus；不放宽六字段 schema、evidence kernel 或 `ready_for_final` 语义。
- 不在运行后修改 task、acceptance、阈值、重试次数、源码或输出。
