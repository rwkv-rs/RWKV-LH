# v18 计划方案与实现 Goal 提示词（基于全历史阅读）

日期：2026-08-15

状态：只读历史阅读后的设计文档；本文件不修改运行时代码，不宣称任何问题已解决。
执行者应以本文件为输入，在实现前自行预注册 Round119 协议。

## 〇、独立数据验证（2026-08-15，不信叙述、只查原始数据）

本计划所依赖的审计结论已经用原始 `results.json`、逐题 `audit.json`、`causal_ledger.json`
独立重算复核，全部精确一致（零出入）：

- 混淆矩阵：R46 `31/32/55/FP24/FN1`、R101 `12/21/32/FP20/FN9`、R116 `8/30/FP20`、
  R117 `20/30/FP8`、R118 Basic30 `21/30/FP9`、R118 Full90 `25/27/60/FP35/FN2`，
  以及 `passed == agent_completed AND external_passed` 的 Strict 定义，均由逐题字段重算。
- TP 转移 R46→R118：保留 18 / 丢失 13 / 新增 7，逐题清单与分析一致。
- 分组：Basic 19(FP9/FN1)、Medium 5(FP15/FN1)、Hard 1(FP11/FN0)。
- M16/M17/M21：`status=running` 且 Final 为空，确认终止事务缺失。
- **M24：50 个 failure key 全部 count=1，而 50 次失败 Action 只有 1 个去重后的失败签名**
  ——双 fingerprint 修复的直接证据。
- H04：完全相同的成功 `list_directory` 33 次；H12：15 个 shard 全部读过（各 2–8 次、共 62
  次成功读）仍无 aggregate；129 次 rollover、7714 causal events、prompt tokens
  16,884,399（均值 8649.8/请求）——状态投影缺失的直接证据。
- Basic30 B10：335,914 prompt tokens、13 个 failure key 各 count=1。
- M10/H09：唯一失败的外部检查是旧事件名 `replan_applied`/`action_returned` 的
  event_min_count——评价 v2 版本化的依据成立。
- B08：11+ 次调用未注册 `verify_checksum`；M30：12 次 `timeout_ms` 被拒后 interrupted，
  两题 External 均 pass——通用能力补全的依据成立。

尚未独立重算（实现者可选复核）：byte-5gram 相似度数值（需运行冻结脚本；注意 R117 的
0.902→0.827 曾被 R118 更正，先例说明必须以脚本输出为准）、47/47 source manifest hash、
Round46 时代逐题叙述。

## 一、阅读范围

- `data/experiments/FULL_HISTORY_AUDIT_AND_V15_DECISION_20260815.md`（Round0–115 全量审计）
- `data/experiments/HISTORICAL_ARCHITECTURE_TRAJECTORY_AND_NEXT_STEP_20260815.md`
- Round116 v15-A / Round117 v15-B / Round118 v17 的预注册协议、REPORT 与
  MANUAL_CAUSAL_ANALYSIS（Basic30 与 Full90 diagnostic）
- 当前源码 `rwkv_lh/model.py`（`_assignment`、`_rollover_if_needed`）、
  `rwkv_lh/controller.py`（`_failure_key`、`_finish_action`、`_terminal_output`）
- `AGENTS.md` 项目规范

## 二、可比结果主线（同一冻结 RWKV-E2E-90）

| 版本 | 样本 | Strict | External | Agent | FP | FN | 结构变量 |
|---|---|---:|---:|---:|---:|---:|---|
| Round46（历史最佳） | 90 | 31 | 32 | 55 | 24 | 1 | 局部五字段 Task、一次直接 Action、真实 Observation 后 decision-last commit、phase-local 上下文 |
| Round50 | 90 | 6 | 11 | 14 | 8 | 5 | 两阶段 selector（工具名→参数）|
| Round53 | 90 | 23 | 24 | 43 | 20 | 1 | 同模型 pre-action reviewer |
| Round80/81 | 90 | 0 | 10 | ≤1 | ≤1 | 10 | 统一 lane + selector 重写 |
| Round101 | 90 | 12 | 21 | 32 | 20 | 9 | v14 前身：Task DAG + Task 内 mini-agent + plan-time evidence 猜测 |
| Round112 | 30 | 6 | 12 | 15 | 9 | 6 | frontier role（被否证）|
| Round116 v15-A | 30 | 8 | 8 | 28 | 20 | 0 | 双 lane Task 脊柱 + 泛化 `lh_task_call` wrapper（被否证）|
| Round117 v15-B | 30 | 20 | 20 | 28 | 8 | 0 | 单 RWKV direct-action spine（方向正确，实现有持久化分裂缺陷）|
| Round118 v17 | 30 | 21 | 21 | 30 | 9 | 0 | + append-only CausalEvent 唯一权威 + 已选 schema 反馈 |
| **Round118 v17 Full90** | **90** | **25** | **27** | **60** | **35** | **2** | 当前状态；Basic 19、Medium 5、Hard+LH 1（LH 0/12）|

## 三、历史证明对 RWKV（弱模型）有效 / 无效的架构

有效（每条都有正反两侧证据）：

1. **operation-specific 直接工具 + 精确 JSON schema，一次提交完整调用。**
   R50 拆两阶段 31→6；R51 只加一个透明 alias 恢复到 17；R116 泛化 wrapper 8/30，
   R117 改直接工具 20/30。
2. **真实 Observation 之后再做完成判断（decision-last）。** R45/46 消除大量 FN；
   R116 把"成功读取"提交为"写 Task 完成"造成 20 FP。
3. **紧凑、局部、靠近当前一步的上下文。** R46 平均 2160 prompt tokens/请求 得 31/90；
   R101 6013 得 12/90；R118 8650 得 25/90。token 越多分数越低，是放大链而非能力问题。
4. **协议拒绝后回显已选 operation 的精确 schema（不换工具、不改参数）。**
   R118：B16/B17 从各 12 次重复拒绝降为 1 次。
5. **集合进度必须是结构化 ledger，不是自由文本。** R55 H12 读 7/15 声称全部完成；
   R118 H12/H14/LH03 全部读完后 rollover 重读。
6. **失败 Observation 是可用事实。** B23 primary 解析失败→backup 分支在 R117/118 稳定成功。

无效（已被多次否证，禁止恢复）：

- 双进度系统（静态 Task DAG + Task 内 mini-agent：R101；双 lane：R116）。
- plan-time `evidence_kind/evidence_subject` 猜测（R101 B15/B19/B20/B26 永久 not-ready）。
- 同模型 reviewer/judge/frontier role/atomicity 预判（R53 -8 Strict；R54 0/15；R112 否证）。
- selector / 两阶段调用 / 泛化 `operation+operation_args` wrapper（R50、R80/81、R116）。
- 自然语言完成声明升级为权威事实（R116 `completion_claim committed`）。
- 微型 canary 通过当作架构提升（R100 4/4 → R101 12/90）。
- Controller 读隐藏验收、补值、改答案、否决 Final（项目红线，从未允许）。

## 四、当前 v17 的架构缺陷（Round118 Full90 逐题归因的五层放大链）

v17 正确地删除了 Task DAG、reviewer 和语义 gate，但把 Round46 的"局部意图 + 局部状态"
也一起删掉了，变成过度无状态的直接行动循环。五个缺陷共同组成一条放大链：

1. **行动意图缺失**：每轮只有 `function+params`，模型不声明本步 objective/done_when。
   → B12 读完文本改用 read_json；LH02 写完 15 个 checkpoint 忘掉 final config；
   35 个 FP 在一次成功 mutation 后直接 Final（Agent 60 而 External 只有 27）。
2. **状态投影缺失**：`LongHorizonModel._assignment()` 只投影最近 ≤12 条 Action；
   `_rollover_if_needed()` 按 12/8/4/2/0 截断，旧 Observation 从在线投影消失（全轮 129 次
   rollover）。没有 per-path 首次/最新观察、成员覆盖集合、最近 verifier 事实、未完成义务。
   → H12 15 shard 全读过后从 shard01 重读；LH03 单目录 list 118 次；LH native 0/12。
3. **失败/成功身份混淆**：`controller._failure_key()` 把 workspace digest 和完整 arguments
   混入 key，write→test 循环中每次写都产生新 key（M24：50 个 key 各 count=1，相同测试失败
   50 次不触发预算）；成功 Observation 完全不计数（H04 相同 list 成功 33 次、H11 成功写 72 次）。
4. **终止事务缺失**：generation outcome unknown 未被 `run()` 捕获，`_terminal_output()`
   只在正常 break 后执行 → M16/M17/M21 停留 `running`、Final 为空（87/90 违反"总要回答"）。
5. **通用能力与评价口径缺口**：缺标准 `move_file`（M28）、`file_digest`（B08）、
   `timeout_ms→timeout` 透明转换（M30，3 题接口性 FN/失败）；官方 v1 验收仍检查旧架构
   事件名（M10 `replan_applied`、H09 `action_returned`），2 题业务正确被判 FP。

量化：18 个 action_count≥20 的用例消耗 75.1% 的 Action；prompt tokens 16.88M 是
Round46 的 4.82 倍。长尾循环已经是质量问题，不只是效率问题。

## 五、v18 方案：Causal Step + Progress Projection

一句话：**给每次直接 Action 一个 RWKV 自己写的当前意图，并让全部真实 Observation 在
rollover 之后仍以确定性投影可见。** 这是对同一个缺口的两面修复，不是补丁并列。

### P0（链路事实完整，先于任何在线质量变量）

1. **Terminal transaction**：捕获 generation outcome unknown；持久化 transport 状态并做有界
   重连；endpoint 恢复后仍由同一 RWKV 生成 `final_answer`。所有退出路径必须追加一个
   terminal causal event（completed/interrupted/failed），不允许 run 停在 `running`。
   Controller 永不合成用户答案。
2. **双 fingerprint**：保留现有 execution/idempotency identity（含 workspace/revision，保证
   重放安全）；新增 `observation_fingerprint` = digest(operation, 显式 target/argv, outcome,
   exit/error/output)，对成功与失败都累计 exact repeat count。相同 traceback、相同 read/list
   结果必须以"第 N 次相同事实"呈现给 RWKV。failure budget 改绑 observation_fingerprint
   （跨 supersede/重命名累计）。Controller 不据 repeat count 生成修复或答案。
3. **通用能力补全**：标准 `move_file`、只读 `file_digest`；透明 `timeout_ms→timeout`（秒）
   转换，保留 raw/normalized/digest，冲突值拒绝。不加任何题目专属 action（不为 H16 加
   `check_invariants`）。
4. **评价 v2 版本化**：保留官方 v1 不动；另行登记 architecture-neutral 的 E2E-90 v2 验收
   （检查可观察行为/因果属性，不检查旧模块事件名），新数据版本、摘要、生成方式全部登记。
   两套口径并列报告，运行后不得改口径。

### P1（单一在线结构变量）

1. **统一因果步 contract**：每次普通调用固定为
   `{"step":{"objective":...,"done_when":...},"function":"<registered_op>","params":{...}}`，
   step 与 action 同一次模型生成；Controller 只验证通用 shape、原样登记 step、执行显式
   function/params。step 不参与任何 Controller 业务 gate，不生成 Task、不建 DAG、不 gate
   Final。`final_answer` 携带最后 step ref 仅作审计。
2. **CausalProgressProjection 替换"最近 12 条"**：从全量 causal ledger 机械生成：
   - 每个 path：discovered/read/mutated 的 action refs、first/latest result digest、最新
     artifact revision、最新 mutation 之后是否有过 observation；
   - 每个成功 list：实际返回成员 + 其中哪些已有 read observation（只陈述覆盖事实，
     不判断业务目标）；
   - 每个 exact observation fingerprint：last result + repeat count；
   - 当前 RWKV step 原文；最后一次协议拒绝；
   - first/latest raw event refs 与 archive digest 保证可追溯。
   rollover 时对相同 fingerprint 折叠计数，保留首次与最新原始 Result 引用。
   投影不得解析隐藏验收、不得算业务汇总、不得标注"应该选择"的成员。

### 明确不做（停止规则，历史已否证）

- 不恢复静态 Task DAG、`evidence_kind/subject`、reviewer、completion gate、递归 subagent、
  frontier role、selector、泛化 wrapper。
- 不根据外部验收阻止/改写 Final；不修改 RWKV 参数或产物；不为单题加路径/字段/答案特判。
- 不用更长 prompt 掩盖状态问题；不把 prompt-replay 说成 native recurrent state。
- 格式转换只搬运显式值；语义字段缺失/冲突一律拒绝，不做第二次语义重采样冒充原答案。

### 验证顺序（按 Round118 建议，Basic30 不再作为晋级证据）

1. 离线结构回归：terminal 事务、双 fingerprint、projection 确定性重建（fold 全量事件 ==
   在线投影）、crash/recovery、工具边界、raw Final、全部现有 pytest。
2. 冻结源码/数据/模型/采样参数（`rwkv7-g1i-13.3b-20260805-ctx16384`、temp 0.05、
   top-p 1.0、top-k 0、max-transitions 200、concurrency 1），生成只读 source manifest，
   直接运行完整 Full90 主运行。
3. 门槛（同时超过 Round46）：Strict ≥ 32/90、FP ≤ 24、FN ≤ 1、90/90 Final 非空且与
   raw RWKV 字节相等、0 个 terminal `running`、Basic ≥ 24 / Medium > 5 / Hard > 2、
   相似度按已版本化 missing-zero 口径报告。
4. 通过后不改源码再跑一次 confirmatory Full90；两轮都过才可称新最佳并 checkpoint。
   任一失败即停止并写 MANUAL_CAUSAL_ANALYSIS，不在失败架构上叠加补丁。

## 六、Goal Prompt v2（英文，十轮迭代版；本节取代第七节存档的 v1 中文单轮版）

方法论变更：不再是一次性 v18 预注册单轮，而是最多十轮（Round119–Round128）的
"分析 → 修根因 → Full90 全量重测 → 再分析"迭代程序。每轮分析必须覆盖全部 90 条
trace（含通过题），以 flip 矩阵和 Round46 TP 保留率防止"只修错题"造成的局部变优、
全局变差（Round47–77 的教训）。§五的单轮验证顺序被本节的循环规程取代。

提示词全文（直接作为 /goal 输入）：

---

# GOAL: Ten-Round Iterative Harness Architecture Program for RWKV-LH (Round119–Round128)

## Context

You work in `/home/chase/GitHub/RWKV-LH` (WSL `UbuntuRecovered`; run all project commands inside WSL; temporary scripts go in `temp/` with absolute paths and descriptive unique names). The project drives a long-horizon agent with a weak 13.3B RWKV7-G1i model. The harness/architecture is the only variable; the model, benchmark, and scoring are frozen.

Current state: architecture v17 — single RWKV session, direct per-operation registered tools, append-only CausalEvent as the only persistence authority, selected-operation schema feedback on protocol rejection. Its frozen full-90 result is Strict 25/90, External 27/90, Agent completed 60/90, FP 35, FN 2. The historical best is Round46: Strict 31/90, External 32/90, FP 24, FN 1. v17 fails not because the model "can't do the tasks" but because of a verified stateless amplification chain (see the Round119 backlog below; every claim there was re-verified from raw per-case data, not from report prose).

## Mission

Run up to TEN experiment rounds (Round119 … Round128). Each round improves the harness architecture so the same frozen RWKV model completes more of the frozen RWKV-E2E-90 suite. End state: the best architecture in project history, demonstrated by a source-frozen full-90 run with Strict > 31, FP <= 24, FN <= 1, plus an unchanged-source confirmatory full-90 run meeting the same bars — then git-checkpoint it. An honest negative (ten rounds, no new best, complete flip history and falsified hypotheses) is also a valid outcome; a bent scoreboard is not.

## Required reading before any change

1. `AGENTS.md` — project discipline: frozen datasets/params/thresholds, no post-hoc metric changes, no per-case special-casing, no auxiliary module replacing model capability.
2. `data/experiments/V18_PLAN_AND_GOAL_PROMPT_20260815.md` — defect diagnosis with independent raw-data verification (section 0), what works / what is disproven for RWKV (section 3), and the v18 candidate design (section 5).
3. `data/experiments/Round118_v17_full90_diagnostic/MANUAL_CAUSAL_ANALYSIS.md` — per-case backward causal analysis of all 90 traces of the current architecture.
4. `data/experiments/FULL_HISTORY_AUDIT_AND_V15_DECISION_20260815.md` — Round0–115 history; at minimum section 3 (trajectory), section 4 (what Round46 did right), section 9 (stop rules).

## THE LOOP — non-negotiable methodology

Every round is exactly: **analyze → fix the root cause → full-90 rerun → analyze.** Nothing else counts as a round.

1. **Analyze ALL 90 traces, not only failures.** Fixing only what failed last round is how this project previously drifted into local optima (Round47–77: each patch chased one symptom and the full-suite score fell from 31 to 0–23). For every case — passing ones included — record the first deviation traced backward from external facts; for passing cases record fragility signals (identical-observation repeat counts, prompt-token blowup, near-miss formats, luck-based recovery). Build the flip matrix versus the previous round AND versus Round46: kept TP, TP→FP, TP→FN, TP→TN, new TP.
2. **Pick the change by evidence, at root-cause altitude.** Global mechanisms only — never task-specific tools, paths, field names, or answer patterns. Prefer ONE coherent structural variable per round so causality stays attributable; bundle only what is mechanically inseparable. Before writing code, preregister `data/experiments/RoundNNN_<NAME>_PROTOCOL.md`: hypothesis, exact change, which observed traces it should affect and how, expected non-regressions, frozen parameters.
3. **Offline gate.** Full pytest, E2E catalog 90/90, crash/side-effect recovery, raw-Final byte equality, compileall, `git diff --check` — all green before any model request.
4. **Full-90 online run.** Freeze a read-only source manifest before the first model request, then run the complete suite (`scripts/run_rwkv_e2e_benchmark.py`, suite all = core30 + LH12 + extension48). Basic30 / canaries / single cases may be used to debug BETWEEN rounds but can never justify keeping a change or claiming progress.
5. **Post-run analysis** in `data/experiments/RoundNNN_*/` (`REPORT.md` + `MANUAL_CAUSAL_ANALYSIS.md`): the fixed metric block below, the flip matrix, a per-case first-deviation table covering all 90, and an explicit verdict: KEEP or REVERT.
6. **Revert rule.** If Strict decreased, or Round46-TP retention decreased, or FN grew beyond the round's preregistered allowance — revert the change completely before the next round. Never stack the next fix on top of a degraded architecture.

## Fixed metric block (report every round, never redefine)

- Strict / External / Agent completed / FP / FN — overall and per group (Basic 30, Medium 30, Hard 18 + LH 12).
- Round46 TP retention (x/31) and previous-round TP retention, with the full flip matrix.
- Total prompt tokens and mean per request; number of cases with >= 20 actions; maximum identical-observation repeat count; protocol rejection count; rollover count.
- Final integrity: 90/90 non-empty Finals byte-equal to raw RWKV output; zero runs left in `running`.

Scoring is frozen: official v1 acceptance stays untouched for all ten rounds. You may create ONCE an architecture-neutral v2 acceptance (replacing legacy event-name checks — M10 `replan_applied`, H09 `action_returned` — with observable-behavior checks), version-registered in `data/datasets/` before its first use, then frozen too. Report v1 and v2 side by side; v1 remains the comparison line against history.

Frozen for all rounds: model `rwkv7-g1i-13.3b-20260805-ctx16384`, endpoint `http://127.0.0.1:29610/v1`, temperature 0.05, top-p 1.0, top-k 0, max-transitions 200, concurrency 1, uv 0.12.5. A round invalidated by auditable endpoint/infrastructure failure may be rerun; model protocol errors, timeouts, and wrong answers are valid results.

## Round119 starting backlog (verified defects of v17)

Five-layer amplification chain, each independently confirmed from raw case data:

1. **No action intent.** Each turn is bare `{function, params}`; the model never states what the current step is for. Add a causal step contract generated in the SAME model call: `{"step": {"objective": ..., "done_when": ...}, "function": ..., "params": {...}}`. Controller validates shape only, records the step verbatim, echoes it back; the step never gates actions or Final, never becomes a Task/DAG. (Evidence: 35 FP finalize right after one successful mutation; B12 switches read_file→read_json on already-read text; LH02 drops the final obligation after 15 checkpoints.)
2. **No durable progress state.** `LongHorizonModel._assignment()` projects only the last <=12 actions; `_rollover_if_needed()` truncates 12/8/4/2/0 — 129 rollovers erased coverage facts. Replace with a deterministic `CausalProgressProjection` folded from the full causal ledger: per-path discovered/read/mutated refs with first/latest result digests and whether the latest mutation was observed afterward; per successful list, the actual members and which of them already have read observations (coverage facts only, no business judgment); per observation fingerprint, last result + repeat count; current step verbatim; last protocol rejection; first/latest raw event refs + archive digest. (Evidence: H12 read all 15 shards 2–8x each yet never aggregated; LH03 listed one directory 118x; LH group 0/12.)
3. **Failure identity fragmentation / success repeats invisible.** `controller._failure_key()` mixes workspace digest and volatile arguments into the key, so an identical failure never accrues budget (M24: 50 keys, all count=1, exactly ONE distinct failure signature repeated 50x) and identical successes are never counted (H04: same successful list 33x). Split into: execution/idempotency identity (keep as is, replay safety) versus `observation_fingerprint` = stable digest(operation, explicit target/argv, outcome, exit/error/output) with exact repeat counts for successes AND failures, shown to the model as fact, budget bound to it across supersedes. Controller never uses counts to pick tools or stop semantically.
4. **No terminal transaction.** Generation-outcome-unknown escapes `run()`; M16/M17/M21 ended `running` with empty Final. Every exit path must append a terminal causal event; persist transport state, bounded reconnect, then the same RWKV produces `final_answer`. Controller never synthesizes an answer.
5. **Generic capability + protocol gaps.** Register standard `move_file` (non-idempotent, copy+delete semantics) and read-only `file_digest` (sha256); transparent `timeout_ms→timeout` (ms→s) conversion keeping raw+normalized values, rejecting conflicts. No task-specific actions (no `check_invariants` for H16). (Evidence: B08 called unregistered `verify_checksum` 11x; M30 sent otherwise-perfect `run_command` with `timeout_ms` 12x; both were external-pass FNs.)

Recommended split: Round119 = defects 3+4+5 (fact-integrity layer, mechanically separable, low semantic risk); Round120 = defects 1+2 (the single online-behavior variable). You may re-derive the split from your own reading, but preregister whatever you choose. From Round121 on, each round's variable must come from the previous round's flip matrix and trace analysis — not from this list's leftover order and not from a single embarrassing case.

## Architecture invariants (proven for this weak model — do not regress)

- Single RWKV semantic lane; no second model, no self-review lane.
- Operation-specific direct tools with exact JSON schemas; one complete call per decision (two-stage selection collapsed 31→6 in Round50; the generic `lh_task_call` wrapper collapsed to 8/30 in Round116).
- Completion decisions AFTER real observations, decision-last (Round45/46).
- Compact, local, current-step context — score correlates inversely with prompt size (R46: 2160 tok/req → 31/90; R118: 8650 tok/req → 25/90).
- On protocol rejection, echo the already-selected operation's exact schema; never switch tools or edit params (B16/B17: 24 rejects → 2).
- Verbatim immutable user request; raw byte-preserved Final; append-only CausalEvent as the only persistence authority; uv Python, bubblewrap, shell=False, workspace scope.
- Collection progress must be a structured ledger of facts, never free-text counting.

## Red lines (disproven or forbidden — reintroducing any is round failure)

- No static Task DAG, plan-time `evidence_kind/evidence_subject`, frontier roles, reviewer/judge of any kind, recursive subagents, or natural-language completion claims promoted to authoritative facts.
- Controller never reads hidden acceptance for online decisions, never rewrites/vetoes the model's Final, never fills in parameter values, never computes business answers or summaries.
- No per-case special-casing of any kind — tools, paths, fields, prompts, or budgets keyed to specific benchmark tasks.
- Format transforms move explicit values only; missing/conflicting semantic fields are rejected, never guessed; no semantic resampling to replace a first decision.
- Prompt replay is never described as native recurrent state.
- Never modify preregistered thresholds, scoring, or datasets after seeing results; never select the better of multiple runs.

## Stopping

- Success: a full-90 run beats Round46 (Strict > 31, FP <= 24, FN <= 1, 90/90 clean Finals, zero `running`) AND an unchanged-source confirmatory full-90 run does too. Git-checkpoint, write the final architecture report, and stop — remaining rounds are only for further preregistered hypotheses, not victory laps.
- If ten rounds pass without a new best: stop, revert to the best KEEP round, and write the final report — best result achieved, complete flip history across rounds, and which hypotheses were falsified by which traces.

---

## 七、存档：v1 中文单轮版提示词（已被第六节取代）

见本仓库根 `AGENTS.md`；提示词全文如下（可直接作为新会话首条消息）：

---

你在 `/home/chase/GitHub/RWKV-LH` 工作（WSL `UbuntuRecovered`，所有项目命令在 WSL 内执行，
临时脚本放 `temp/` 并用绝对路径）。这是一个用 13.3B RWKV7-G1i 弱模型驱动长程 Agent 的
研究项目。你的任务是实现并运行 **Round119 v18 "Causal Step + Progress Projection"**。

先读（必读，按序）：
1. `AGENTS.md` — 项目纪律：固定数据集/参数/阈值、运行后不得改口径、禁止用例特判、
   禁止辅助模块取代模型能力。
2. `data/experiments/V18_PLAN_AND_GOAL_PROMPT_20260815.md` — 本任务的完整方案（就是本文件）。
3. `data/experiments/Round118_v17_full90_diagnostic/MANUAL_CAUSAL_ANALYSIS.md` — 当前
   五层缺陷与 v18 设计依据。
4. `data/experiments/Round118_V17_CAUSAL_EVENT_AUTHORITY_AND_SCHEMA_FEEDBACK_PROTOCOL.md`
   与 `Round118_v17_basic30_official/MANUAL_CAUSAL_ANALYSIS.md` — v17 已冻结的结构与结论。

背景一句话：v17（单 RWKV、直接注册工具、append-only CausalEvent 唯一权威、已选 schema
反馈）Full90 = Strict 25/90 / FP 35 / FN 2；历史最佳 Round46 = 31/90 / FP 24 / FN 1。
v17 的失败不在"模型不会做"，而在四项无状态放大：无 step 意图、rollover 只留最近 12 条
Action、failure key 混入 workspace digest 使相同失败永不触发预算、generation outcome
unknown 无终止事务。你要在 v17 单脊柱上修这四项，且**只修这四项加通用能力补全**。

实现范围（P0 → P1，全部在现有 v17 模块上，不新建并行架构）：

P0-1 终止事务：`rwkv_lh/controller.py` 的 run 循环与 `_terminal_output()`。捕获模型
generation outcome unknown（传输层异常）；持久化 transport 状态、有界重试；恢复后由同一
RWKV 生成 final_answer。每条退出路径必须追加 terminal causal event；任何 run 不得停留
`running`/空 Final。禁止 Controller 合成答案。

P0-2 双 fingerprint：保留 `ActionRecord` 现有 idempotency/execution identity 不动；新增
`observation_fingerprint` = 稳定 digest(operation, 显式 target/argv, outcome_type,
exit_code, error, output)，对成功与失败 Observation 都累计 repeat count 并写入
causal event 与模型可见 Observation（"exact_repeat_count": N）。把
`controller._failure_key()` 的预算键改为 observation_fingerprint（移除 workspace_digest
与易变 arguments 造成的 key 碎裂），跨 supersede 累计。repeat count 只呈现事实，
Controller 不据此选工具/改参数/终止语义。

P0-3 通用能力：在 `rwkv_lh/harness.py` 注册标准 `move_file`（copy+delete 语义、非幂等
标注）与只读 `file_digest`（sha256）；在 model_io 转换层加透明 `timeout_ms→timeout`
（毫秒→秒，保留 raw/normalized，冲突拒绝）。不加任何题目专属 action。

P0-4 评价 v2：不改官方 v1。新建 architecture-neutral 的 E2E-90 v2 验收数据集版本
（把 M10 `replan_applied`、H09 `action_returned` 这类旧事件名检查替换为可观察行为/因果
属性检查），在 `data/datasets/` 登记来源、版本、摘要、生成方式。两套口径并列报告。

P1-1 因果步 contract：模型 wire 协议改为
`{"step":{"objective":"...","done_when":"..."},"function":"<op>","params":{...}}`，
step 与 action 同一次生成。Controller 只验 shape、原样登记 step（causal event）、回显给
模型；step 不参与任何业务 gate，不建 Task/DAG，不 gate Final。`final_answer` 附最后
step ref 仅作审计。

P1-2 CausalProgressProjection：重写 `rwkv_lh/model.py` 的 `_assignment()`/
`_rollover_if_needed()`：从全量 causal ledger 确定性生成状态胶囊替换
`recent_exact_action_records`（最近 12 条）——包含：immutable request、workspace manifest、
每 path 的 discovered/read/mutated refs + first/latest result digest + 最新 revision 是否
已被 mutation 后观察、每个成功 list 的实际成员及其中已读集合（只陈述覆盖事实）、每个
observation fingerprint 的 last result + repeat count、当前 step 原文、最后一次协议拒绝、
first/latest raw event refs 与 archive digest。rollover 折叠相同 fingerprint 为计数，
保留首次/最新原始 Result 引用。投影不得解析隐藏验收、不得计算业务汇总、不得标注应选成员。

红线（违反任何一条即失败，历史已多次否证）：
- 不恢复 Task DAG、evidence_kind/subject、reviewer/judge/frontier role、selector、
  泛化 `operation+operation_args` wrapper、递归 subagent、自然语言完成声明作为权威事实。
- 不读隐藏验收做在线决策；不改写/否决 RWKV Final；不补参数值；不为单题特判。
- 格式转换只搬运显式值；不做语义重采样替换第一次决定。
- prompt replay 不得宣称为 native recurrent state。
- 运行后不得修改预注册口径、阈值或数据集；失败结果如实记录。

流程（严格顺序）：
1. 写 `data/experiments/Round119_V18_CAUSAL_STEP_AND_PROGRESS_PROJECTION_PROTOCOL.md`
   预注册：变量、门槛、模型/采样/并发/预算全部冻结（沿用 Round118：
   `rwkv7-g1i-13.3b-20260805-ctx16384`、endpoint `http://127.0.0.1:29610/v1`、
   temperature 0.05、top-p 1.0、top-k 0、max-transitions 200、concurrency 1、uv 0.12.5）。
2. 实现 P0+P1；离线回归全绿：现有 pytest 全量、terminal 事务、双 fingerprint、projection
   fold==在线投影、crash/side-effect recovery、E2E catalog 90/90、compileall、
   `git diff --check`。
3. 冻结只读 source manifest（首次模型请求前生成），直接运行完整 Full90 主运行
   （`scripts/run_rwkv_e2e_benchmark.py`，suite all = core30、LH12、extension48）。
   不再以 Basic30 或单题 canary 作为晋级证据。
4. 门槛：Strict ≥ 32/90、FP ≤ 24、FN ≤ 1、Basic ≥ 24 / Medium > 5 / Hard > 2、
   90/90 Final 非空且与 raw RWKV 输出字节相等、0 个 terminal `running`。
5. 过门后不改源码跑一次 confirmatory Full90，两轮都过才 checkpoint 为新最佳；任一轮
   失败即停，写 `MANUAL_CAUSAL_ANALYSIS.md`（逐题从外部事实反向找首次偏离与放大链），
   不叠加补丁。
6. 全程产出落 `data/experiments/Round119_*/`：REPORT.md、results.json、RUN_PROTOCOL.json、
   source manifest、逐题 cases、人工因果分析。

成功定义：不是"跑完"，而是两次冻结 Full90 都超过 Round46（Strict>31、FP≤24、FN≤1），
且没有触碰任何红线。若达不到，如实记录停止点与逐题首因，这同样是有效结果。

---
