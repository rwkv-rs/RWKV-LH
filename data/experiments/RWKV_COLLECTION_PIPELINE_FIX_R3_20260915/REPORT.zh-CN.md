# 管线修复 R3

任务级：复用已有两道公开检查任务，2/2 完成并符合事前忠实报告要求，submitted 2、mutation 0，均 answer_submitted；没有项目 Strict 或训练收益结论。模型角色级：4 次真实生成、0 协议拒绝，完整输入 15,215 token、输出 290 token，输入重建/State 父链/观察及纠正快照 4/4 核验。两题记录的执行耗时合计 140.50 秒，不是规模吞吐基准。

正式训练新增 0，强模型纠正调用 0；两道历史来源仅工程冒烟，不计入新的 3 万条。未启动正式长跑。物理 GPU 0 身份已通过远端 nvidia-smi 确认，UUID GPU-1faf7f09-25f4-2515-b707-6e0766aa841d。服务器未执行 Git，也未变更部署；本地原 29613 隧道缺失已恢复，服务实际 capabilities 正常。

## 已完成的工程整改

- Q1：事务内先检查冻结材料，再领取；预检查失败保持 pending。
- Q2：未决 running 返回明确非零，不伪装完成；仅通过已落盘、身份及摘要一致的收据恢复。真实子进程 os._exit(9) 后恢复一次、无重复派发的回归通过。
- Q3：领取和读取清单检查 payload SHA，冻结任务清单、实际运行包文件（含非 Python 文件）、入口/依赖锁及运行设置。冻结后不能新增任务。服务 server_build 绑定既有完整 engine/project manifest attestation，另绑定 tokenizer/model/context；每 worker 开始前复核。
- Q4：结果 task ID 与 source/payload 绑定；逐任务原子收据 fsync、持久进程池、完成即入账，不等待慢批次。执行结果先保存，外部验收随后更新；两者不混为任务通过。
- Q5：全库存私有来源/验收文件与所有可见工作区及输出树隔离，跨题泄露回归通过。
- Q6：非法 role 类型明确记录；坏 JSON 等格式隔离。流式审计每 100 行保存带源前缀/输出摘要的检查点，中断续扫不重复行；完整前只有 .partial。
- Q7 的字节级部分：唯一原始题目行 SHA 索引防止换 ID 重复纳入，status 索引支持规模领取。跨来源语义/家族去重仍属于待构建库存的上游工作，未宣称已经解决。
- 生产采集接入既有 generation_snapshot_audit，不改模型输入和答案；真实 4 个生成边界全部通过现有 validate_generation_snapshot。
- 持久全局截止、基础设施错误停发计数及显式恢复确认；重启不会自动延长时间或清掉故障计数。保留在途结果，不强制总结。未知 worker 结果没有收据时保守停下，尚不自动续接未知 Native 请求。
- 私有验收契约要求 explicit manual_rubric 或 stdio_exact；前者待外部语义审核，后者复用隔离验证器判断产物，最多 30 秒，异常记 unreviewable，不改答案或标为完整任务合格。
- 增加不占主进程锁的 --status，显示队列状态及已记录任务的调用/提交/证据完整统计，方便约三小时检查。

## 验证

red.txt：新增失败回归先复现。green.txt：队列、故障调度及 UltraData 相关 38 项通过。完整最终源码回归 full_tests_final.txt：1859 passed、0 skipped，357.87 秒。full_tests.txt 是更早实现快照的 1856 passed，期间后续补充修复，不作为最终源码验证替代。

真实调用从新 CLI 完成入队、冻结、执行及逐任务收据。SMOKE_REGISTRATION.json 在运行前登记；SMOKE_AUDIT.json 验证唯一构造函数 bootstrap/event append 与实际输入 token 完全相同，State profile/父 digest 正确，工具观察进入最终回答上下文，快照完整。最终答案与真实 stdout/退出码逐项核对，两个任务均无无依据作者声明或文件改动。MANUAL_REVIEW.json 为独立验收记录，不改原始 RESULT/收据中的 pending_manual_review。

## 本轮按 owner 要求暂缓与剩余边界

磁盘自动监控、跨卷自动清理及 State blob 回收暂不扩展，保留队列卷最低空间检查；约三小时人工查看不等于已实现自动 State 生命周期回收。未粗暴删除生产 blobs。

Native 全局请求锁保持不变，不在这一轮直接删除共享状态保护。客户端最大有效并发仍需针对真实题型实测；本轮默认 1，不宣称已经取得最大吞吐。

SFT-Agent 环境复建、3 万条原题/家族去重与正式任务冻结尚未完成；现有 54 个审计来源不等于可执行任务。需要人工语义验收的题目也不能通过机械指标自动判合格。下一阶段先完成可运行库存和并发实测，再启动规模采集，无需为这一步启动训练或教师纠正。

本轮修复了列出的队列和证据通路缺陷，但不是“所有工程风险永久清零”或“3 万题已经开跑”。owner 五处既有修改保留，未混入本轮提交；不 push。

owner 后续明确正式数据服务于真实 Coding Agent：范围已登记到 docs/CODING_AGENT_COLLECTION_SCOPE.zh-CN.md。不把本轮两道运行检查的工程冒烟误当成主要任务分布，也不以泛问答填充规模。
