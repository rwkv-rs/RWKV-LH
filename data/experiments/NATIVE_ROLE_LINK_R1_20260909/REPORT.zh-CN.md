# NATIVE_ROLE_LINK_R1_20260909

Agent 最近实测为 `ULTRADATA_COLLECTION_R1_20260909`：三题 **Strict 0/3、completed 0/3、mutation 0、动作 0**，均在 Native 状态初始化处 `model_transport_unavailable`，共 24 次 HTTP 400。Planner 三题均被接纳，第一题经一次原始输出语义纠正。新修复尚须独立三题运行测量，不能重评分原结果。

角色级：原轮 Selector 和其他角色实际生成数均为 0，没有生产角色候选，也没有 optimizer steps。本轮真实 State 传输探针通过 create、append、import 三项操作，导入前后 State digest 与 cache binding 一致；没有生成请求、Agent 任务或角色标签。

## 根因

本地 Native 客户端与服务器已经冻结部署的 journal 接口没有接通。服务器 `prepare_native_request` 要求恢复协议及请求 ID，并拒绝自行补齐后的请求体与原请求不同；本地七个 State 方法直接调用 HTTP，缺少所需恢复身份。健康检查只检查基础操作布尔值，丢掉 request_recovery 声明。Controller 又忽略 `RWKVHTTPError.retryable=false`，将每个明确的 400 重试八次。

这影响所有共用该 Native 客户端的角色和任务，发生在 Selector 实际请求之前的 Executor 状态 bootstrap。题目 ID、Planner 步数、模型参数量和 StateTune 样本质量都不是这次 400 的根因。原始错误、冻结代码、实际服务能力与双方文件身份见主工作树的 UltraData R1 报告、SOURCE_REGISTRATION 和服务 attestation。

## 修改

1. 新增仅负责传输身份的 `runtime/native_request_protocol.py`：固定当前恢复协议、规范 JSON 的 operation/body 摘要、非生成操作的稳定请求 ID；生成必须保留 ModelSession 已分配的 ID。未知协议、无效 ID 或非有限 JSON 明确拒绝。所有 Native 状态变更共用此输入构造，不按任务或模型枚举兼容分支。
2. Native 七个入口共用一次 POST 和原请求结果查询。在超时、连接丢失、可重试 HTTP 错误或损坏响应后，只查询原 ID / operation / body digest，校验结果摘要与状态，不重新提交模型工作；未知、冲突或损坏回执保持结果未知。
3. `RuntimeCapabilities` 保留并验证当前 request recovery 声明；缺失或未知恢复协议不能再通过 durable Native 准入。模型/State/token metadata 继续通过原生产会话绑定，未修改角色 parser、输入协议或停止边界。
4. 共享 Controller 的四条错误处理路径根据错误类型和明确 retryable 属性停止自动重试。结果未知、传输协议矛盾和不可重试 HTTP 保留原始失败；已知发生在提交前的可重试连接故障仍走原恢复预算。

五角色、唯一输入 builder、底模、State 形状、服务端部署及解码器不变。修复没有添加辅助模型、工具特判或合成训练数据。

## 验证与边界

传输回归在修复前源码上得到 22 failed，修复后 22 passed；覆盖七个入口、响应丢失后的单次执行、原生成 ID、metadata 保留、错误回执与缺失/未知能力声明。最初测试夹具漏传 api_key 的准备错误及修正后的原源码红测分别保留，不把夹具错误作为根因证据。

Controller 三项回归原先每次调用 8 次，修复后仅 1 次。定向传输/会话 117 passed；恢复边界 7 passed。完整回归首遍 1141 passed、2 failed：旧“瞬时连接故障”夹具实际抛出“生成结果未知”，并期望重新采样，现改为真实提交前的连接故障；结果未知单独由新增回归验证。最终完整测试及 SHA 在 `VALIDATION.json` / `EVIDENCE_SHA256.json`。

真实 State 探针的第一次准备在本地 builder 因空工具定义而拒绝，尚未提交任何 State 操作；补用现有定义后完成三项服务器操作，原尝试保留。探针使用当前 ModelSession 构造输入，只检验 State 传输，不是角色能力测试或正式样本。

本轮仅验证进程内传输恢复和当前错误重试边界；没有把它声明为跨进程 prepared-request 自动恢复、Native State 全生命周期回收或最终 Agent 验收。实际生成/审计/工具/完成路径须在随后独立冻结的生产运行观察。训练仍按当前角色证据与预算推进，不以 Agent 已高分为先决条件。
