# 真实 Agent 采集管线

正式任务范围以 [Coding Agent 采集要求](CODING_AGENT_COLLECTION_SCOPE.zh-CN.md) 为准：真实仓库修复、实现、反馈及相关理解/验证，泛问答不用于凑数。

目标为 30,000 个独立、可复建任务的真实执行；静态 SFT 轨迹不是新的执行，任务收据不是训练准入。SFT-Agent 和项目来源优先，RL 代码/长文补充。本轮修复运行管线；3 万条任务清单和 SFT 环境仍需完成复建与冻结，不能把工程回归当作规模采集结果。

## 来源审计与入队

`scripts/audit_collection_sources.py --source /absolute/source.jsonl --revision <40位修订SHA> --output /absolute/audit.jsonl` 流式结构审计。输出先写 `.partial`，每 100 行落盘恢复点，全部处理后才成为最终文件。中断后使用 `--resume`，核对源前缀和已写输出摘要后继续，不重复计行。异常格式单列，不冒充正确轨迹或可复建环境。

`scripts/run_collection_queue.py --queue /absolute/queue.sqlite3 --inventory /absolute/admitted.jsonl` 事务性纳入任务。每行必须包含 source_id、source_path、source_sha256、environment_sha256、acceptance_path、acceptance_sha256、job。

source_path 是保留的原始题目行文件，不能指整个共享容器后把行编号丢掉。逐行 SHA 重复和相同 source_id 均拒绝；跨来源相似任务仍需上游家族去重，不宣称字节去重解决语义重复。

验收文件只接受两种显式约定：`manual_rubric` 配非空 criteria，或 `stdio_exact` 配 cases 和 `comparison=exact_rstrip`。浮点容差、多解及其他不适用 exact 的题目不可伪装 stdio_exact。前者等待独立语义审核；后者复用隔离 stdio 验证器，仅判断代码产物，不把它算作完整回答忠实性。外部验证最多 30 秒，超过则记 unreviewable；原始执行收据在验证前已经保存。

所有源轨迹及验收文件均须位于全部模型可见工作区之外，也不能被任何任务输出覆盖。job 字段严格为 task_id、request、workspace、output_dir、tool_scope、max_calls、max_seconds。tool_scope 仅 files / inspect / coding，拒绝 assistance/on_stall。模型自主选择工具及参数；不注入参考答案或计划步骤。

工作区摘要为 `SHA256(json.dumps(tree_identity(workspace, allow_links=False), sort_keys=True, ensure_ascii=False, allow_nan=False).encode())`。派发前检查源、验收和工作区真实字节；失败保持 pending、停止派发，不冒充在途任务。

## 执行、停止与恢复

执行入口：`scripts/run_collection_queue.py --queue /absolute/queue.sqlite3 --run --concurrency 1 --max-hours 36`。仅允许 zero State；冻结实际运行包全部文件、入口、依赖锁、任务清单、运行参数及服务身份。Native server_build 绑定服务器核验过的 engine/project manifest，另冻结 tokenizer_build、模型与上下文。每个 worker 开始前重新检查服务身份。不得在运行中改冻结源码或参数。

持久进程池只保留有界在途任务，完成一个即写入队列，不等待整批。任务收到真实模型结果后，保存带 source/task/payload/result 摘要的原子收据；编码及只读任务均接入生成边界工作区快照，沿现有生产输入/State 路径执行。

pending → running → recorded。recorded 只是结果落盘。启动时核验收据，恢复已完成条目；无有效收据的 running 明确报未决并返回非零，不能自动重试。此版本不自动重建未知 Native 请求续跑，需要依据真实 trace/Native 收据确认后处理，不能用重跑掩盖中断。

到全局截止后停止派发、收集在途结果；截止时间持久化，不因重启延长。连续基础设施/不完整 trace 达到 `--failure-limit`（默认 3）停发，状态跨重启保留。确认服务恢复后可显式 `--acknowledge-recovery` 清除停发计数，操作时间有记录，旧结果不删除。模型正常结束的错误答案不按基础设施错误处理。

每次任务的最长生成执行时间受剩余全局预算约束；截止附近仍可能有最多 30 秒外部验收及收据收尾。已完成队列正常返回；未决、预算到期、预检查或服务故障返回非零。

## 约每三小时检查

`--status` 使用 SQLite 只读连接，不抢占正在执行的主进程锁。显示 pending/running/recorded，并从已落盘结果统计发生模型调用的任务、提交、trace 完整和验收状态；这些结果计数不包含仍在 running 的任务，也不把 submitted 当作合格。

示例：`.venv/bin/python scripts/run_collection_queue.py --queue /absolute/queue.sqlite3 --status`。

按 owner 最新指令，本轮不扩展磁盘自动监控/清理，不实现自动 State blob 删除。保留现有队列所在卷的低水位检查（默认 20 GiB）。人工检查时仍应查看远端 State/工作区存储；本地低水位不代表服务器容量。

Native 服务全局请求锁保持原样，不直接移除。实际并发/吞吐仍需实测；客户端并发数不代表 GPU 真正并发。默认并发 1，未宣称“最大稳定并发”已经得到。

## 开始规模采集前

完成 SFT 原始环境复建、跨来源家族去重、任务与验收冻结，核验模型/服务部署身份，然后对实际题型做有界试跑和吞吐测量。现有工程冒烟仅复用历史两道任务，不计入新的 3 万条，也不测训练收益。不得读取最终 holdout；当前训练后固定 12 题及衍生内容仍排除出未来训练。仅 GPU 0，不启动教师纠正或训练。
