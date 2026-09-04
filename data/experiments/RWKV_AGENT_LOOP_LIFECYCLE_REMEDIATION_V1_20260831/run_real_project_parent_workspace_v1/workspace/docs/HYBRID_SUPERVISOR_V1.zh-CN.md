# Hybrid Supervisor v1 初步架构

日期：2026-08-21

基线：R126 v19-P1（`baseline/round126-v19p1`，`50754a2`）

分支：`chase/hybrid-product-v1`

## 目标与边界

Hybrid v1 在已验证的 R126 单 RWKV Action lane 外增加一个可选强模型边界，解决“执行模型
能操作，但长任务规划与完成判断不稳定”的产品问题。它没有增加第二个执行 Agent：

| 组件 | 有权做什么 | 明确无权做什么 |
|---|---|---|
| Strong Supervisor | 生成一次结构化计划；对 RWKV 完成候选返回 PASS 或 REVISE | 选择/执行 Harness 工具；修改工作区；改写 Final |
| RWKV Worker | 在唯一持久 Action lane 中选择直接工具；读取 Observation；产生 Final | 跳过工具参数校验；把 Supervisor 意见伪装成已观察事实 |
| Controller/Harness | 校验协议；执行 RWKV 明确调用；持久化事实；限制返修次数 | 生成业务计划；补写工具参数；生成或改写业务答案 |

未注入 Supervisor 时，Controller 继续走 `single-rwkv-direct-action.v1`。这不是降级模拟，而是
原 R126 默认路径。注入后架构标签为 `strong-supervisor-rwkv-worker.v1`。

## 固定生命周期

1. Controller 把不可变请求、约束和有界 workspace manifest 交给 Supervisor。
2. Supervisor 返回经 `SupervisorPlan` 严格校验的 objective、steps、completion checks 和 risks。
3. 计划以 `supervisor_plan_committed` 写入因果链，再作为有来源标记的 ModelEvent 进入同一
   RWKV Action lane。
4. RWKV 独立选择直接工具，Harness 返回真实结果；这条执行链与 R126 相同。
5. RWKV 发出 `final_answer(text)` 后，Supervisor 获得计划、原始请求、候选文本、当前工作区
   manifest、有界 Action 记录和 artifact 摘要，只能返回：
   - `PASS`：Controller 原样交付 RWKV 文本并标记完成；
   - `REVISE`：具体问题作为 ModelEvent 返回同一 RWKV lane。
6. 默认只允许一次返修，配置硬上限为三次。耗尽时状态为 `interrupted`，不会伪报 completed。

这里没有 Supervisor↔RWKV 自由对话，也没有多个 reviewer 相互校验，因此不会形成无界调用
环。每一个计划、检查、失败和返修都有 provider/model 归属与 CausalEvent 记录。

## API 适配契约

OpenAI-compatible 适配器位于 `rwkv_lh.supervisor_openai`，并实现
`rwkv_lh.supervisor.SupervisorClient`：

```python
class SupervisorClient:
    provider_name: str
    model_name: str

    def create_plan(self, request: SupervisorPlanRequest) -> SupervisorPlan: ...
    def review_final(self, request: SupervisorReviewRequest) -> SupervisorReview: ...
```

适配器负责把厂商响应解析成字段，再通过 `SupervisorPlan.create(...)` 和
`SupervisorReview.create(...)` 建立本地值对象。Controller 不接受裸字符串、自然语言判定或
未经校验的 dict。计划必须至少有一个 step 和 completion check；REVISE 必须有具体 issue；
PASS 不得同时携带 issue。

当前适配器具备连接/读取超时、有限 transport retry、请求/响应摘要审计、ignored `.env` 密钥、
严格 JSON schema 输出和 provider rate-limit 分类。API 读取超时或连接中断按 outcome unknown
fail-closed，不盲目重复生成。已落盘计划或检查由 Controller 恢复，不会再次调用 provider。

## 失败与恢复语义

- Supervisor 规划失败：写入 `supervisor_call_failed(phase=plan)`，运行 fail-closed 为 failed，
  RWKV 不开始执行。
- Supervisor 检查失败：写入 `supervisor_call_failed(phase=review)`，候选保留但运行状态为
  interrupted，不能当作已批准完成。
- 非法计划或检查对象等同 API 失败，不做猜测或容错改写。
- 计划提交后进程退出：resume 从因果链恢复，不再次调用 planner。
- PASS 检查提交后、`run_completed` 前进程退出：resume 使用已提交候选原样完成，不重复调用
  RWKV 或 reviewer。
- REVISE 提交后进程退出：resume 恢复同一个 review ModelEvent；event id 去重避免重复反馈。
- RWKV Final 已提交但尚未写入检查时进程退出：resume 从持久 decision 恢复同一候选，不让
  RWKV 重新生成；未知结果的 Supervisor 调用仍需重试并留下审计记录。
- 已进入 Hybrid 的运行必须继续注入 SupervisorClient；缺少配置时 fail-closed，不能静默降级为
  纯 R126 绕过完成检查。

## 当前完成与未完成

已完成：provider-neutral 数据契约、Controller 可选接线、一次规划、PASS/REVISE 检查、返修硬
上限、fail-closed、因果审计、关键 crash recovery 和专项测试。

已完成：OpenAI-compatible 强模型 HTTP 适配器、E2E CLI 配置入口、真实 JSON-schema API
联调。尚未完成：本地 UI 配置入口、固定数据集上的 Hybrid Full90、费用/延迟预算和生产密钥
轮换管理。

## v1.1 在线微任务控制面

Round134 验证的是上述“一次静态 Plan + 终局 Review”，不等于在线指导。可选
`SupervisorPolicy(mode="online_microtask")` / CLI `--supervisor-strategy online_microtask`
使用独立生命周期：

1. GPT-5.4 初始只给一个带验收条件的微任务，不输出 Harness 调用或参数。
2. RWKV 在同一持久 Action lane 中连续选择并执行工具。正常每 6 个 actions 形成一个执行波次；
   两次相同且 workspace digest 不变的 action 会提前结束波次。
3. 连续 2 个没有执行 action 的协议拒绝也形成一个有界波次，让 GPT 聚焦纠正工具契约理解；
   schema 本身不放宽，GPT 仍不构造调用参数。
4. GPT-5.4 用一次 `next_directive` 同时验收最新波次并布置下一件微任务。RWKV 用
   `final_answer` 报告当前微任务完成；Supervisor 可以接受为顶层 Final，也可以继续派工。
5. 每题默认最多 64 个 directive，失败和预算耗尽均 fail-closed。每个 directive、所验收的
   action ids、provider/model、usage 和 digest 都写入审计；GPT action count 恒为零。
6. 独立 workspace 的 case 由 runner process pool 并发，所有底层工具调用仍来自 RWKV。
   同一 workspace 暂时保持单一 mutation lane，避免并发写覆盖或破坏 RWKV state 连续性。

这一模式的目标是让 GPT 成为低频 Planner/Reviewer，让低成本 RWKV 承担大量工具动作和并发
执行。它不把 GPT verdict 当成训练真值；正式标签仍由 frozen isolated verifier 与 workspace
evidence 决定。
