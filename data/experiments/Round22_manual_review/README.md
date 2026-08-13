# Round22 全 90 题人工因果审阅

## 目的

本目录不是聚合脚本报告。Codex 逐题打开冻结的 visible task、initial workspace、`model_trace.json`、
`event_log.json`、`state_timeline.json` 和 artifact/workspace 结果，先重建 score-independent 生命周期；
随后才连接 hidden acceptance、标准答案和 Round21 对照。机械工具只用于定位记录、计算哈希和检查遗漏，
不自动生成“根因”判断。

## 每题固定审阅顺序

1. **输入边界**：用户目标、初始 workspace、模型实际收到的首次 prompt。
2. **Goal**：RWKV raw output → parsed payload → Controller materialized Goal；记录丢失、增加或错误绑定。
3. **Plan**：raw → parsed → normalization → TaskGraph；检查任务覆盖、依赖、粒度、priority 与 criterion claim。
4. **执行**：每个 task 的 action choice、G1i raw/parsed/normalized payload、Harness 参数、真实返回和 artifact。
5. **状态传递**：action result、snapshot、dependency projection、后继模型 prompt 中实际可见的内容。
6. **验证与恢复**：deterministic verifier、witness mode/selection/binding、proof、CriterionEvidence、obligation、
   retry/replan 与 suppression。
7. **终态**：第一个不可逆偏离点、后续放大事件、terminal cause；区分 RWKV 生产错误与架构放大。
8. **标准答案后连接**：只在前七步冻结后检查 External/Strict、failed checks、reference 和 Round21 变化。
9. **归因结论**：逐项标记 `observed` / `strong_inference` / `unknown_counterfactual`，不把相关性写成因果。
10. **结构需求**：只描述该题暴露出的能力缺口，不在单题阶段确定下一轮实现方案。

## 事件关联规则

- protocol block 必须通过其前驱 `request_id` 和事件邻接关系连接到真实失败请求；不能简单选择“该 task
  最后一次 tool_action”。Round22 原盲态聚合在 B09 等题存在这种错配。
- 一次 protocol error 是否得到纠错必须检查其后是否存在同 request type 的新 `model_request_started`，
  不能因为源码存在 `range(1, 3)` 就假定第二次请求实际执行。
- artifact 正误必须用冻结 workspace bytes 与 acceptance 后验连接；action 返回 `written` 不是目标正确证据。
- 正确产物但未完成记为 completion false negative；不得反向据此把 verifier/proof 判为应该通过。

## 状态

- Round23 方案制定暂停；未发送任何 Round23 RWKV 请求。
- 先完成 Basic 30、Medium 30、Hard 30 的逐题记录，再生成跨题缺陷图。
- 已完成 Basic `E2E-B01`–`E2E-B30` 共 `30/30`，Medium `E2E-M01`–`E2E-M30` 共 `30/30`，
  Hard `E2E-H01`–`E2E-H18` 与 `E2E-LH01`–`E2E-LH12` 共 `30/30`；总进度 `90/90`。
- 当前条目文件位于 `cases/`；分析器事实校正位于 `ANALYZER_CORRECTIONS.md`。
- B01–B20 的非最终横向复核位于 `BASIC_B01_B20_INTERIM_CAUSAL_MAP.md`；它只登记已复现模式与待证反事实，
  不作为 Round23 实现方案。
- Basic 30题的完整横向因果合成位于 `BASIC_B01_B30_CAUSAL_SYNTHESIS.md`；它仍只用于形成待验证结构假设，
  不直接确定Round23改动。
- Medium 30题的完整横向因果合成位于 `MEDIUM_M01_M30_CAUSAL_SYNTHESIS.md`；其中保留Round21→22的进步、回归、
  防作弊边界与待Hard验证假设，不作为最终实现方向。
- Hard 30题的完整横向因果合成位于 `HARD_H01_LH12_CAUSAL_SYNTHESIS.md`；它连接了长链、事务、external effect、
  lifecycle与零执行案例，并区分RWKV真实错误、架构放大和尚未测到的能力。
- 全90题逐题最短反向因果链位于 `CROSS_90_CASE_CAUSAL_INDEX.md`；它逐题登记“终态 ← 放大环节 ← 最早偏差”，
  用于核对跨题结论没有遗漏或只凭频次决定方向。
- 全90题最终结构归因和分阶段修改指导位于 `CROSS_90_ARCHITECTURE_GUIDANCE.md`；它提出以RWKV决定为核心的
  因果状态机、明确防作弊边界、文件落点、实施顺序和分层验证指标。Round23仍未启动，修改前须据此单独预注册。
