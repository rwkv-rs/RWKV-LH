# COORDINATOR_ACTOR_MINIMAL_VERIFIER_VALIDATION_R1_20260911

## Agent 结果

固定 `realprojectdevv1` 12题真实运行：**Strict 0/12、completed 0/12、external passed 0/12、mutation 0、动作14**。终止原因为 Coordinator 计划不可用10题、Runner observation 投影异常1题、重复成功读取耗尽无进展预算1题。没有错误宣称完成；没有外部已通过而系统拒绝完成的样本。

候选可行性门没有通过，不能据此切换生产架构。生产入口、`rwkv_lh/`、评分、题集和验收均未修改；没有训练、新建数据集版本或读取 Holdout。运行前两次尝试分别被 tool-disclosure 配置冲突和本地13.3B隧道缺失拒绝，均发生在输出目录和题目运行之前，不计12题分母。恢复既有 `29613 → 18234` 隧道后，模型身份与 Native recurrent State 能力核验通过。

## 角色与架构证据

专项确定性测试 `tests/test_hybrid_supervisor.py tests/test_unified_controller.py` 为 **46 passed**；提交前完整回归为 **1502 passed、0 failed、0 skipped，256.67秒**。真实运行共24次 Coordinator 请求；10题两次计划都未被本地 `SupervisorPlan` schema接受，只有 RP-MAINT-01 和 RP-WEB-02 在第二次请求取得计划并进入 Actor。两题共18次 RWKV请求、14个动作，全部生成记录的 lane id 均为 `LANE:ACTION`；工具名与完整参数在同一输出中生成。独立Selector、三菜单投票、Step Auditor、Stage Checker、Finalizer和Final Auditor调用均为0。

Minimal Verifier 正常 review 调用为0：RP-MAINT-01在8次只读动作后触发 `ObservationProjectionError: list_directory returned a non-JSON structured result`；RP-WEB-02在6次只读动作后因重复读取结束，终止边界取得RWKV未完成说明，但状态为interrupted，没有宣称完成。

## 根因和结论边界

第一系统性失败在 Coordinator 协议边界。现有 `OpenAICompatibleSupervisorClient.create_plan` 要求顶层 `objective/constraints/steps/completion_checks/risks`，但没有像其他强模型入口那样在 `SupervisorPlan.create` 语义校验失败后携带具体错误重试。当前 DeepSeek 的真实返回包含完整规划内容，却使用了 `plan` 步骤数组或嵌套 `plan.goal/plan.steps`，因此被拒绝为 `steps must be non-empty` 或 `objective must be non-empty`。程序不应从任意字段猜计划语义；正确修复是把具体 schema 错误反馈给同一个 Coordinator，要求它重新生成唯一规范对象。

本轮证明候选链的直接Actor和持续单lane能够真实运行，同时否定“旧候选实现可直接用于当前服务”的假设。它没有测到正常Minimal Verifier效果，也没有达到候选可行性门。下一工程轮应先补 `create_plan` 的有界语义修复回归，再用相同公开开发题重新验证；旧0/12保持原评分，不重评分。
