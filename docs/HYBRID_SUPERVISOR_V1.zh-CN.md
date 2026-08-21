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

具体厂商 API 暂未绑定。适配器必须实现 `rwkv_lh.supervisor.SupervisorClient`：

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

建议后续 API 适配器具备：连接/读取超时、有限 transport retry、请求/响应摘要审计、密钥只从
环境或 secret store 读取、严格 JSON schema 输出、provider rate-limit 分类。API 重试不能重复
提交已落盘计划或检查。

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

尚未完成：具体强模型 HTTP/API 适配器、CLI/本地 UI 配置入口、真实 API 联调、固定数据集上的
Hybrid 对照实验、费用/延迟预算和生产密钥管理。这些必须在拿到 API 的协议、模型名、限额和
输出能力后完成，不能由当前代码猜测。
