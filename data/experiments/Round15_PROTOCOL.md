# Round15 预注册：Semantic-Minimal Goal-Obligation Replan Envelope

预注册日期：2026-08-13（任何 Round15 RWKV 请求之前）

## 固定依据

Round12--Round14 的 score-independent lifecycle 对比显示，见证/证明链已经逐级深入：

- Round12：32 题到 precommit、6 题形成 witness catalog、0 题 proof pass、0 题保存证据；
- Round13：34 题到 post-action selection、1 题编译、0 题 proof pass、0 题保存证据；
- Round14：38 题到 selection、19 题编译、16 题到 proof、5 题 proof pass，且这 5 题各保存
  1 条 `verified` CriterionEvidence。

Round14 的旧分析曾因只统计不存在的 `criterion_evidence_committed` 事件、且把 keyed-map 状态误当
list 而报告 evidence=0。重新核对最终 RunState 后已纠正为 5 题；这属于分析仪表修复，不是 Agent
行为修改。权威多轮因果分析 SHA-256：
`8371c4a666bdcec2bdedbc4f00b9d0894d1ae4c74c8b22e44d22fbb873eacd40`。

Round14 Goal-obligation replan 的独立、非计分分析覆盖 52 题、204 次真实请求：

- 73 次 `ok`，131 次 contract error；其中 127 次发生在顶层 exact-key gate；
- 83 次响应的 parsed payload 顶层只有 `new_tasks`，分布于 43 题；83/83 都是非空对象数组，
  82/83 每个任务具有 ID/title/description，77/83 每个任务都带 criterion binding；
- 这些响应没有被现有 task/criterion/dependency/scope validator 检查，因为在语义验证前即被顶层
  `schema_version/reason/new_tasks` exact-key gate 拒绝；
- 另外 39 次根本没有 `new_tasks`，5 次把 capsule 等额外字段与 `new_tasks` 混在一起，不能归入
  最小合法外壳。

上述分析不读取 hidden acceptance、external checks、用户题面或 Codex reference。Round14 obligation
分析 SHA-256：`454dc0e95585658ca3f91f0d9d1f8394b33b4dca5e45539577909cd40d721cd4`。

Round14 后置成绩为 External `22/90`、Strict `0/90`、Completed `0/90`、FP `0`、FN `22`；
它没有通过 Git 晋级门，未上传。

## 唯一结构变量

实施 `semantic_minimal_obligation_replan.v2`，只把请求类型已经确定的传输元数据从 hard gate 降为
可选审计字段：

1. 顶层唯一语义必需字段为 `new_tasks`；允许的字段仍仅限
   `new_tasks/schema_version/reason`，任何其他顶层字段继续拒绝。
2. 若 RWKV 提供 `schema_version`，必须精确等于 `long-horizon.obligation-replan.v1`；缺失只记录
   `rwkv_schema_version_provided=false`，Controller 不补造版本文本。
3. 若 RWKV 提供 `reason`，必须是字符串并原样保存；缺失只记录
   `rwkv_reason_provided=false`，内部 reason 保持空字符串，不生成“unresolved Goal evidence”等替代理由。
4. `new_tasks` 原样进入既有 `_task_nodes`、64-task 上限、task contract、Goal criterion、local ID、
   dependency、active-completed dependency、unresolved criterion 与 graph materialization 校验。任何语义
   失败仍 fail closed，不尝试挑选、删除、重排、补全或改写任务。
5. prompt 要求最小 `{new_tasks:[...]}` 外壳；旧的完整 v1 外壳仍可被原样接受和审计。

这是一个单一协议变量：在已经由 request type 定义语境的边界上，移除重复的版本/解释文本强制项。
它不修改 RWKV 提出的任务，也不让规则决定任务正确与否。

## 不作弊边界

- 不根据 external pass、标准答案、artifact 相似度或历史通过来选择或放行任务。
- 不从 capsule 复制缺失任务，不生成 local ID、title、description、criterion、dependency、priority、
  retry policy 或 reason。
- 不接受只有 task object、criterion object、capsule echo 或带未知顶层字段的响应；必须明确具有唯一
  `new_tasks` 数组字段。
- 所有 raw/parsed、字段 presence、原始 task objects、校验错误、materialized ID 映射和状态变化完整审计。
- final answer 仍只能是 RWKV 原始输出；hidden acceptance/reference 只在 90 题全部终止后加载。

## 明确不改

- Round14 的 post-action witness selection、WS/WH、Goal literal、proof、evidence 与 completion 不改。
- Goal 容量、初始 plan、普通 failure replan、priority、G1i action、recovery、sampling、并发、预算、
  max transitions、数据、验收和相似度算法不改。
- 不把 obligation task 自动标成完成，不复用 external verifier 作为 CriterionEvidence，不增加规则答案。

## 固定运行与验证

- RWKV-E2E-90 v1，Basic/Medium/Hard 各 30；模型
  `rwkv7-g1i-13.3b-20260805-ctx16384`，endpoint `127.0.0.1:29610/v1`。
- 并发 8，max transitions 200，sampling 与 Round14 一致。
- 运行前后完整产品测试、LH-Control-30；冻结源码、协议、数据和 runtime fingerprint。
- 保存 90/90 prompt/raw/parsed/event/state/workspace；先做 score-independent backward causality，再加载
  standard answer/acceptance。

## 预注册诊断门

- `new_tasks`-only payload 不得再因缺少 schema/reason 被拒绝；presence 必须可审计，缺失值不得冒充
  RWKV 输出。
- 其他顶层 shape、空/非法 tasks、ID/criterion/dependency/scope 错误继续 fail closed。
- obligation top-level contract error 应从 Round14 的 127 次显著下降；至少 30/43 个受影响 case 应有
  一次 proposal 通过完整语义校验并保存，且 saved obligation replan case 数高于 Round14。
- Round14 已达到的 19 个 compiled selection、5 个 proof-pass/evidence case 不作为每轮固定下限，因为
  采样会改变题目轨迹；但若全部归零，必须做逐题迁移归因，不能声称整体成功。
- FP=0、Offline 全过、Control 30/30、因果链 90/90、需要 final 的 case raw byte equality全过。

## GitHub 晋级门

恢复并继续执行严格门：只有同时满足 FP=0、Strict >7、Completed >7、External 不低于 22、全量回归
和审计通过，才允许提交并推送。否则保存本地 Round15 结果并记为 `do_not_upload`；远端保持 Round2
checkpoint `b5aa2b2d64036f41aab3ccdc20b2cbfb718e5dbe`。
