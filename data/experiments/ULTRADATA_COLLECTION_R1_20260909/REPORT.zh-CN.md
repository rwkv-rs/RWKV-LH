# ULTRADATA_COLLECTION_R1_20260909

Agent 实测：固定三题 **Strict 0/3、completed 0/3、mutation 0、动作 0**。三题均以 `model_transport_unavailable` 让出，状态保留为可恢复的 running，不是完成。没有单题墙钟预算耗尽，未换题、未重评分，生产源码与启动冻结一致。

角色级：三题的初始计划均由 `gpt-5.6-sol` 生成并被当前 Controller 接纳；第一题首次输出的 required_phases 存在重复，经既有一次语义修复后通过。三题共 4 次 Planner 请求，未到 Stage Checker。Selector / Executor / 三个后续角色均没有完成生成调用；Native State 初始化失败在实际 Selector 请求之前。唯一抽取器审计三份完整来源后得到 Selector 候选 **0**、optimizer steps **0**。

## 根因与证据

生产每题都触发 8 次同类错误，共 24 次 HTTP 400：`invalid request recovery identity`。这不是题目 ID 格式错误，也不是模型输出长度不足。服务器当前部署的 Native journal 要求所有状态变更携带 `recovery_protocol` 和绑定请求体的 `request_id`；本地 `OpenAICompatibleRWKVClient` 的 create/append/fork/commit/rollback/import 没有发送该身份，generate 也没有恢复协议字段。服务在模型 State 操作执行前拒绝请求。

上游健康检查仅确认基础状态操作布尔值，忽略服务器声明的 `request_recovery` 及其协议版本，因此错误地通过预检。下游 Controller 把明确不可重试的 HTTP 400 当普通瞬时传输故障，重复初始化 8 次。问题影响共享 Native 传输层及四个生成角色，不限于三道 Code 题、某个模型尺寸或路径。

原始来源在 `all_zero/cases/`，包括 SQLite、model trace、event log、timeline 和 causal ledger；原文及含私有验收的 audit 仅保存在本地。`SOURCE_REGISTRATION.json` 和 `selector_candidates/manifest.json` 绑定完整源码、角色协议与逐工件 SHA，未用私有验收或作者参考作为标签。`SUMMARY.json` 的终止和错误信息直接取 canonical causal_event；首次分析误读外围 event-log 层的记录保留为 `ANALYSIS_ATTEMPT_01.json`，原始工件和成绩未改动。

## 冻结与验证

- 题目为 owner 提交的 UltraData 首轮固定 3 题，来源和 88 个发布 I/O 测试沿用原试点清单；这些是公开算法任务，不声称真实用户 trace 或模型未见过原题。
- 运行前对 7 份可见公开题目目录做 429 对 byte 5-gram cosine 检查，最大约 0.175720，低于预注册 0.95；不读取 Holdout。
- Planner / Stage Checker 为当前强模型配置；Selector 为 2.9B，其余四角色为 13.3B，五个角色均显式 zero。Planner 8192、Stage 2400 tokens；顺序采集、每题 200 transitions / 1200 秒、总 3600 秒。详见 `REGISTRATION.json`。
- 服务实际权重重新计算 SHA；上传 engine 的 6395 个文件、Selector 项目的 118 个文件、Executor 项目的 132 个文件均通过对应冻结清单核验。服务器没有调用 Git。身份材料分别在 `REMOTE_ATTESTATION.json`、`EXECUTOR_SOURCE_ATTESTATION.json` 和 `EXECUTOR_CAPABILITIES_RAW.json`。
- 基线源码为 `d40f3a69`，沿用该版本完整回归 1118 passed、0 skipped；本轮采集没有修改生产源码。准备脚本一次公开题目字段映射错误在模型请求前修正并保留记录。

## 下一轮

修复共享 Native 请求身份、结果查询恢复及能力协商，并禁止 Controller 自动重试明确拒绝或结果未知的请求。修复在独立工作树进行，当前三题结果保持原始基线；新源码通过完整回归后重新冻结三题采集，不能把这些初始化失败训练成 Selector 能力问题。

本轮既有切分为 train / dev / train，尚缺独立 confirmation family。后续从真实运行补齐当前角色的预注册数量、覆盖、合法标签、服务器完整 token 及固定回归后，按已有授权进入训练登记。Agent 低分和后续角色未到达不是训练禁令；这里没有任何可训练生成边界。
