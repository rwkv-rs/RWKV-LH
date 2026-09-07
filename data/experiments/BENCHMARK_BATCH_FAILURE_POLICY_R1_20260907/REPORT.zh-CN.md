# 单题 Supervisor 失败与批量中止策略分离

Agent 级：本修复没有模型调用，也没有新增 Strict、completed、mutation 或终止原因结果。R5 已在 A 仅 1/12、B 未启动时停止，旧结果由主代理保留为 INCOMPLETE/INVALID，不按新策略重评分、不接续。后续全量观测必须新冻结。

根因：runner 的串行路径在记录当前题结果后，遇到 `supervisor_failure.failed && !retryable` 就 break；并行路径对同一条件取消其余 pending future。这里的 retryable 原本表达单次 Supervisor 请求能否重试，HTTP 200 返回的 length、非法 JSON 等模型输出失败也会被记为 retryable=false。直接把该字段用作整批中止条件，使“本题不再重试”错误地变成“后续所有题不运行”。两条路径汇入同一 RUN_ABORTED/exit 3，因此 sequence 无法获得完整分母，也无法开始 B。

本轮仅修改 runner 及对应测试，不改 rwkv_lh、Supervisor adapter、parser、字段合同、采样、token 预算、State、单题循环或评分公式。新增显式 CLI：

```
--supervisor-batch-failure-policy continue_model_failures
```

默认仍为 `stop_non_retryable`，所有未显式选择新策略的套件继续原规则。新策略由串行和并行共同调用 `should_abort_supervisor_batch()`；它只决定是否继续其他题，不修改当前 result、retryable、trace 或分数，也不向当前题添加重试。新策略写入 RUN_PROTOCOL；发生中止时 RUN_ABORTED 同时记录策略及原始分类。

| 情形 | 显式 continue_model_failures 的行为 |
|---|---|
| 无 Supervisor failure | 继续原流程 |
| category=protocol、HTTP 200、error 以 SupervisorProtocolError: 开头 | 保留该题原失败，运行下一题；不根据 length/JSON 内容关键词特判 |
| category=semantic_validation、HTTP 0、error 以 TypeError: 或 ValueError: 开头 | 保留该题原本地语义合同失败，运行下一题 |
| authorization / endpoint / request / model_identity / configuration，或 HTTP 401/403/404 | 停止整批，即使错误被标成 retryable=true |
| 无 HTTP 200 的 protocol、非 SupervisorProtocolError 的 protocol、未知或 Controller boundary 非 retryable 错误 | 沿原规则停止整批 |
| upstream、connection 等原来 retryable=true 的临时传输失败 | 保留原批量行为；没有增加单题 transport retry 或 resume 次数 |

边界：当前 failure summary 对 HTTP 400 只有 request 分类，无法可靠区分上下文过长和全局请求配置错误，所以仍保守停止。不以自然语言错误消息猜测 context，不扩宽 parser，也不承诺本策略能把任意配置故障变成完整 12 题。身份 preflight 与实验 wrapper 的源码、服务、模型及前后身份核验仍保留；批量策略不能代替这些检查。

全局排查确认只有上述两个 batch 中止点以及共用 RUN_ABORTED/exit 3 收尾。并行原有行为保留：发生 fatal 时仅取消可取消的 pending future；已运行的 future 仍由原 as_completed 路径记录结果，不编造未运行题结果。完整分母与两臂资格继续由冻结 wrapper/collector 检查。

先写测试并运行旧代码，`RED_TESTS.log` 为 **31 failed in 0.54s**：CLI/default、16 个分类边界、实际 benchmark.main 串行与并行 12 个组合。main 测试仅 mock 题集加载、健康检查、run_case 和 executor 调度，调用次数、结果文件、原始 failure、取消行为、RUN_ABORTED、retry manifest 均由实际主循环产生；没有模型、外部端点或角色协议输入。

修复后最终 `GREEN_FINAL_TESTS.log` 为 **46 passed in 0.38s**：31 项新测试加既有边界文件 15 项，其中实际 metadata 测试确认显式策略登记。单题 protocol/semantic failure 下串行和并行均遍历全部人工题，返回 exit 2，逐题失败未改变且每题只调用一次；默认模型失败、授权/request/unknown 非 retryable 仍保持整批中止。完整 tests/ 由主代理在 Planner no-CoT 修复完成后统一执行，本报告不预填最终通过数字。

所有测试及本次修复都未读取 Holdout、未生成模型、未训练或新建角色数据集。代码已停写等待主代理 review，未提交。根因和验证证据的 SHA-256 见 `SOURCE_SHA256.json`。
