# PLANNER_STRONG_ROUTING_R1_20260909

Agent：没有新增完整 Strict / completed 分数；本轮 Planner 检查没有执行 Agent 动作，mutation 为 0。此前 R3 的 12 题运行由 owner 暂停，仅 10 题有终止记录，不能报告为完整 12 题成绩。角色级：五个 RWKV 角色没有新增正式训练数据或 optimizer steps；生产 Planner 检查尚未提交有效计划，原始终止仍包含 `strong_planner_unavailable`。完整回归 **1102 passed，0 skipped，187.10 秒**，不能作为 Agent 能力改善的替代证据。

## 根因与整改

1. 默认配置分裂：Supervisor 默认加载 `.env`，Runtime 加载 `.env.local`，两者都使用 `setdefault`；初始化次序决定先进入环境的 Planner 配置。两个文件仍指向 13.3B，已有 `.env.strong.local` 的强模型配置没有被默认入口选中。本轮统一到 `.env.local`，迁入既有 `gpt-5.6-sol` 路由，清除旧路由和冗余强模型配置文件。Planner / Stage Checker 独立配置，五个 RWKV 角色值保持一致，没有重新部署模型或恢复旧架构。
2. 完整 JSON 被解析器拒绝时，`GoalPlanPatch.from_model_value` 抛出的 ValueError 丢失原始对象；Controller 的下一次纠错只有错误字符串。现在通过 `GoalPlanResponseError` 携带独立复制的原始 JSON；顶层、阶段、步骤、义务的字段错误包含 missing/unexpected 信息。Controller 将原始对象写入拒绝事件与请求尾部，仍由原 Planner 生成完整修正，不改名兼容未知字段，不补根目录，不接纳旧版本。
3. 初始/续写计划合同错误曾抛 RuntimeError，进入“服务不可用”分支。现在完整对象的这类错误进入已有语义纠错；传输失败与不完整输出仍分开处理，未接纳的计划不改变活动计划。
4. 原生 RWKV 拒绝 `length`，通用聊天却能接受带完整 JSON 的 `length`。现在 Goal Planner / Stage Checker 的聊天输出也必须自然 `stop`。这修复了更换 backend 后的完成判定差异。
5. 当前强模型网关对完整非流式请求返回过 HTTP 500，同一输入的 SSE 诊断成功。本轮增加模型名称无关的 `RWKV_LH_PLANNER_STREAM` 配置；默认 false，当前网关设 true，原生 RWKV 保持自身非流式传输。接收标准 SSE 事件，保持请求串行锁直到读完，完整拼接后才做 JSON 和合同校验；缺少 DONE/finish、多个 choice、模型身份变化、结束后追加内容和非法事件均拒绝。读取预算耗尽仍中断，不执行半份计划。

## 验证与真实连接证据

- 修复前的准确基线重现：`RED_VERIFIED.log` **18 failed**。初始单元 fixture 曾遗漏 `goal_digest`，其旧 RED 日志不用于缺陷证据；修正 fixture 后在本地原提交 `d13f28407350194cc051579d611b849710e27197` 重现，并核验恢复了全部当前源码。
- 流式功能：`STREAM_RED.log` **8 failed**，实现后原定向组 **223 passed**；追加配置隔离与读取截止验证后 `STREAM_GREEN_FINAL2.log` **10 passed**。原生 fixture 本身包含 `stream=false`，期间修正了一条错误测试断言；一轮完整测试由开发者中断并保留记录，最终从头运行全部 `tests/`。
- 最终 `FULL_TESTS.log` **1102 passed，0 skipped，187.10 秒**；包括 Torch / State、必需浏览器、历史 Controller 路由与唯一协议检查。修复前后校验未读取 Holdout，也未修改/重评分 R3。
- `STRONG_PROVIDER_MODELS.json`：既有网关 GET models 成功，列出配置的模型。模型目录响应不等于生成可用性，也不是权重级 attestation。
- `PLANNER_SMOKE_*`：两次完整非流式 Planner 调用均返回 HTTP 500。第一次检查脚本有未配置 Selector 的前置失败（0 调用），另一次清理错误导致未保存内存中的原始 HTTP 正文；Controller 持久事件保留，限制写入 `SMOKE_ATTEMPT_LEDGER.json`。
- `PROVIDER_DIAGNOSTIC_RESULT.json` 与 `TRANSPORT_TINY_SYSTEM.json`：极小 user-only / system+user 请求均 HTTP 200，返回 `gpt-5.6-sol`、stop。这排除了“完全无法访问”及“所有 system 消息都不兼容”的解释。
- `TRANSPORT_PLANNER_STREAM.json`：同一完整 Planner 输入开启 SSE 后 HTTP 200，返回 `gpt-5.6-sol`、stop、DONE，当前 GoalPlanPatch 和滚动计划校验通过，耗时 **29.97 秒**。这是诊断证据，不是 Agent 成绩或生产角色训练数据。
- `PLANNER_STREAM_SMOKE_RESULT.json`：真正接入新适配层后的首次响应 HTTP 200、stop，输入 **1929 tokens**、输出 **521 tokens**。义务的 `required_phases=[]` 不满足现有合同，解析器保留原始计划并发出语义纠错；该纠错请求 HTTP 500。没有耗尽 8192 输出预算，没有提交计划。
- `REPAIR_TRANSPORT_RETRY_RESULT.json`：对完全相同的纠错请求另行登记一次传输恢复检查，仍 HTTP 500，错误类别是上游 `do_request_failed`。没有自动切回 13.3B，没有循环枚举模型或改变验收口径。

所有连接尝试均有独立预算登记，旧失败没有覆盖成成功。两次初始 Planner、一个极小诊断、两个格式/流式诊断、两次生产流式调用和一次原样纠错恢复，共 **8 次生成请求**；不是训练轮次。流式成功支持选用该响应方式，但不证明网关内部故障根因，也没有消除其间歇性 HTTP 500。

## 当前配置与限制

Planner / Stage Checker 配置为 `gpt-5.6-sol`，backend `openai-compatible`，stream=true；Planner 输出上限 8192、Stage Checker 2400，读取超时 240 秒，默认传输最多 2 次、语义纠错 1 次，fallback 为空、缓存关闭。数值是资源上限，不是计划步数限制；服务返回的模型名不能证明第三方实际加载的权重身份。

本轮解决的是已重现的本地配置、错误归属和接收链路问题。不能宣称 Planner 生产验收、Stage Checker 实测、完整 Agent 闭环或 StateTune 已完成；网关仍有 HTTP 500，强模型也并非每次都遵守协议。跨进程恢复时语义纠错与 pending 的衔接未在本轮真实检查中闭合，后续须单独验证，不应把原样适配层重试算作 Controller 自动恢复。

2.9B 服务和已完成的 Native 数值兼容验证保持有效；训练驱动 WIP 留在独立工作树，未并入本轮、未运行正式优化器。整套评测和训练保持 owner 暂停状态。外部数据用途见 [资源接入判断](../../../docs/OPEN_SOURCE_RESOURCE_ADOPTION.zh-CN.md)。文件与脚本身份见 `EVIDENCE_SHA256.json`、`SCRIPT_SOURCES.json` 和各请求登记；密钥没有进入记录或 Git。
