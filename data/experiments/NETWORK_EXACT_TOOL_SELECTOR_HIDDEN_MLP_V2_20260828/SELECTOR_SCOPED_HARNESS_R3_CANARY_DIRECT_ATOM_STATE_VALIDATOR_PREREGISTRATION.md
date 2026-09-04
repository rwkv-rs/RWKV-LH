# Selector scoped-Harness R3 canary：direct atom-state validator 预注册

日期：2026-08-30

## 目的

只读裁定 `SELECTOR_SCOPED_HARNESS_SUBSET_REMEDIATION_R3` 的真实 canary 是否跨过原始架构缺陷，同时验证 Selector 原始 25-logit 输出、Executor 原始文本、Selector→Executor handoff 以及 contract-graph 权限边界均未被改写。

本裁定不评价 Agent 任务质量。B01/B02/B04 的能力通过率单独报告，不得用本完整性裁定掩盖。

## 为什么使用 direct atom-state validator

当前架构为 `strong-planner-reviewer-rwkv-contract-graph.v2`。每个 RWKV atom 有独立 `LongHorizonStore`；顶层 coordinator state 只保存 contract graph 与 atom outcome，不复制 atom 的模型 checkpoint。旧 validator 假设全部 checkpoint 位于一个顶层 state，因此不适用于当前架构。R1、R2 失败记录作为无效验证保留，不修改源证据。

本轮直接、只读打开 24 个 `atom_workers/*/*/state/long_horizon.db`，分别恢复 `RunState`；顶层 contract graph 和聚合 `model_trace.json` 另行验证，不把不同 atom 的 state 合并或投影成伪单 state。

## 冻结输入

- 固定案例：`E2E-B01`、`E2E-B02`、`E2E-B04`。
- 固定 atom DB 数：B01=5、B02=7、B04=12，总计 24。
- 固定 model request 数：B01=42、B02=34、B04=31，总计 107。
- 固定 action 数：B01=2、B02=5、B04=15，总计 22。
- 固定 Selector 输出数：committed/consumed=79，rejected=3，总计 82。
- 源 `results.json`、`RUN_PROTOCOL.json`、三个 `audit.json`、三个 `model_trace.json`、24 个 DB、修复代码、定向测试和 R1/R2 无效记录的 SHA-256 固定在 validator 的 `FROZEN_INPUTS` 中。
- validator 与本协议的 SHA-256 在运行前写入独立 execution freeze；运行后不得改变阈值或评价口径。

## 固定身份

Selector：

- model：`rwkv7-g1i-2.9b-vllm-v1`
- model SHA-256：`01f39dd59fc402fbe8ba49765a1997ee9dbc82427bf0ece6a4fac520e9eb8044`
- head SHA-256：`721669ce8733b590b3aa6c910d8bc13d744612f1fee884d5276a3f0d96d0d441`
- head hash：`205f995690232aef9c442b19a009fb2eda4c6be4e524e3fc903bb2dd17d72f9e`
- feature protocol：`rwkv-lh.vllm-rwkv-final-hidden-mean-last-concat.v1`
- input protocol：`rwkv-lh.exact-tool-selector-input.v7-requirement-byte-tail`
- state profile：`zero` / 64 个 `0`
- 类别菜单：冻结 25 类，顺序必须与 `NETWORK_EXACT_TOOL_LABELS` 完全一致。

Executor：

- model：`rwkv7-g1i-13.3b-exe-g3-g6-deterministic-cmix-r7-multiprofile-ctx2496`
- model SHA-256：`5d97772ba04a81bdaeba90e1d6d306c70560bf4f784522be61cdcade69e30562`
- task-level profile：`EXE-G3-MULTISTAGE-STEP2000`
- profile SHA-256：`13f6586951666962405286dda8e45c1eae82a37c68c21b3b75dbbb04c6e54f12`

## 固定算法与门槛

本轮不使用语义判断。相似性/完整性算法固定为 canonical JSON 字段精确相等、UTF-8 byte-exact SHA-256、集合双射和整数计数相等；所有门均要求 100%。

1. 24 个 SQLite DB 只能以 `mode=ro&immutable=1` 打开；每个 DB 恰有一个 `runs` 行，`run_id=ATOM`，row revision、goal digest 与恢复的 `RunState` 完全一致，`RunState.from_dict` 投影重建成功。
2. 每个 Selector checkpoint 必须满足固定身份；每个 Executor checkpoint 必须满足固定身份；lane head 必须引用同 lane 的已保存 checkpoint。
3. 每个已提交 handoff 的 raw selection 必须经 `NetworkExactToolSelection.from_dict` 校验，并与其 `raw_record()` 完全相等；必须 25 个有限 logits、原始 argmax、`postprocessed=false`、`generated_text=false`。handoff 的 Selector/Executor parent checkpoint 必须存在且身份匹配。
4. 每个 `exact_tool_selection_rejected` 同样执行 raw-record 完全相等校验；只接受 `operation_not_authorized_by_active_harness`，且 `action_executed=false`。不得存在重映射、mask、rerank 或替代执行。
5. 每个 case 的聚合 trace 中 `generation_started == generation_returned == atom outcome model_request_count == atom RunState decision count`；每个 request 一一对应。每个 returned candidate 必须恰好 committed 或 rolled back 一次。
6. 每个 raw generation 的 `raw_output` 与外层字段 UTF-8 byte-exact；SHA-256、byte count、token IDs、model、profile、sampling 和 `postprocessed=false` 均验证。RunState decision 的 `request_id/raw_output/accepted` 与 trace commit/rollback 完全对应。
7. 顶层协议必须是 contract-graph v2；Planner/Reviewer 无工具执行权限。全部 graph patch/batch/atom outcome 必须记录 `rwkv_action_authority=true`、`supervisor_action_executed=false`，atom outcome 另需 `controller_rewritten=false`，Planner concrete operation count 必须为 0。
8. 三个 audit 及全部相关路径中旧异常字符串 `menu differs from the active Harness` 出现次数必须为 0。
9. audit 声明的 causal artifact SHA-256 与磁盘文件完全一致；输出 non-intervention policy 保持原值。
10. 验证前后所有冻结输入 SHA-256 完全一致；本验证发出 0 次 Planner、Selector、Executor 或 Harness 请求。

总通过条件：以上全部 gate 为真；预期结构计数精确为 24 DB、107 request/decision、82 raw Selector output、22 action。任务能力仍按 canary 原始结果报告，不能因完整性通过而改写为能力通过。

## 输出

- `CONTRACT_GRAPH_ATOM_STATE_INTEGRITY_R3.json`
- `READONLY_DIRECT_ATOM_STATE_VALIDATOR_R3_RESULT.json`

两个文件都是派生证据；禁止覆盖 canary 原始文件或旧 validator 输出。
