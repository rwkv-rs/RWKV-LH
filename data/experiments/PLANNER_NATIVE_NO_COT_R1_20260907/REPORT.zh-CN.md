# Planner 原生 no-CoT 适配记录

本轮没有新增 Agent 级 Strict / completed / mutation 或完整双零成绩。owner 明确要求 Planner 使用现有 13.3B，但不使用推理 / CoT；本轮只调整 Planner 的原生生成边界，Stage Checker 及其他角色保留原行为。一次与生产输入 SHA 匹配的真实 no-CoT 探针由独立代理执行，结果待其独立证据文件归档，本报告不预填成功、失败或模型成绩。

现部署 `rwkv_defaults` 的 `fake_think` 前缀精确为 `<think></think`，最后一个 `>` 由模型续写；Planner 使用这一已有原生格式，随后直接输出 JSON。Stage Checker 继续使用 `open_think` 和 `<think`。生产 [supervisor_vllm_rwkv.py](../../../rwkv_lh/runtime/supervisor_vllm_rwkv.py) 的 `envelope_for_phase` 分别绑定 `goal_plan` / `goal_stage_review`；请求构造和响应解码均要求显式 phase，删除了会被两个角色误共用的全局输入边界常量。

[supervisor_openai.py](../../../rwkv_lh/supervisor_openai.py) 的请求审计记录实际 input / prompt / prefill SHA、generation_mode 和 zero 身份。缓存身份通过同一个生产 wire builder 绑定实际阶段、请求体和模型；响应恢复仅拼回本次真实发送的 prefill。Planner 原始 completion 必须以 `>` 开头，随后除空白外直接是 JSON 对象，并满足自然 stop 和既有严格 JSON / GoalPlanPatch 合同；额外 CoT、解释性正文或截断均拒绝。原始输出保留于审计，不能删除模型产生的思考来伪装直出。Stage Checker 的思考边界保持原样。

canonical 协议 payload 与原有 builder 不变，Planner 8,192 / Stage Checker 2,400 输出预算、16,384 物理上下文、采样与各角色 State 职责保持不变，仍显式 zero State。no-CoT 边界正确不代表模型字段合同或 Agent 能力通过。

验证使用实际日志，没有重新执行测试：

| 验证 | 实际结果 | 日志 SHA-256 |
| --- | --- | --- |
| [修改前红测](RED_TESTS.log) | 8 failed / 51 passed，0.40 秒 | `ce6a094893f07b358f037ff508721dc06ca9f58ff74d37b29d5eed38a13dac36` |
| [no-CoT 定向绿测](GREEN_TESTS.log) | 59 passed，0.07 秒 | `43137f3677f0ff061bc8d695dc62c2badb2448c6380c6b203faa06b245007ec1` |
| [包含批量策略修复的完整回归](PYTEST_FULL.log) | 811 passed，60.96 秒 | `0ed851133dad3f2527d6e801faacc1413e3dde7b788a83539b879fd484186aa3` |

红测覆盖 Planner 精确 wire、保留 canonical 请求与原始审计、无 token IDs 的兼容元数据行为、未知 phase 拒绝、额外推理拒绝及空白 JSON 边界；绿测证明这些代码合同通过。完整回归属于本次隔离源码及联合批量策略修改，不验证原目录其他任务的未提交代码，不等同模型评测。

R5 首题的 protocol length 及旧冻结结果保持原样，不能按新 decoder 重评分或拼入 R6。R6 将以最终源码、逐阶段原生 wire 和明确批量失败策略重新冻结，使用全新 workspace / State 从头运行完整同 12 题 A、B 两臂；本报告不预告执行完成。未授权角色训练，没有读取 Holdout 或隐藏验收。

[SOURCE_SHA256.json](SOURCE_SHA256.json) 仅记录当前相关生产源码、回归文件、上述三份日志和本报告 SHA；不改原始日志或其他轮次工件。真实探针及后续 Agent 运行以各自独立证据为准。
