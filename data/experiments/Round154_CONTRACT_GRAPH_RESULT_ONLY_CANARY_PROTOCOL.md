# Round154：Contract Graph Result-Only 13-Case Canary 预注册

日期：2026-08-23

## 固定架构

`strong-planner-reviewer-rwkv-contract-graph.v1`：

- compact GPT-5.4 Planner=low reasoning，一次编译 obligations、RWKV DAG、frozen finalizer；
- deterministic scheduler + transaction-isolated parallel RWKV atoms；正常 ready batch 不调用 GPT；
- independent GPT-5.4 Reviewer=medium reasoning，只读 result capsules，不读 RWKV prompt、transcript、
  arguments、candidate、worker summary 或 retry/rejection 过程；
- required obligations 全部 satisfied 后执行 RWKV finalizer，原样交付 Final。

代码回归固定为 151 passed。训练数据仍不生成。

## 固定运行参数

- cases：B22、M15、LH06、B09、M24、H09、M10、LH04、LH08、M28、LH09、B04、M16。
- case concurrency=4；RWKV atom concurrency=4；GPT 跨 case 串行。
- transport retry=3；semantic repair=2；plan tokens=4000；review tokens=2400。
- max graph patches=8；review rounds=8；graph atoms=48；stagnant rounds=2；max transitions=200。
- full tool disclosure；固定 verifier、sampling、任务与评分。

Round148 同一子集：strict 2/13，logical GPT requests=79（均值6.08，范围4–13）。

## 晋级门

质量：

1. strict >=11/13；B04、M16 正例均保留。
2. B09/M24 至少一题由 FN 转 TP，且无新增 external-pass/agent-interrupted FN。
3. B22/M15/LH06 至少两题由 FP 转 TP。
4. H09/M10/LH04/LH08 至少两题完整公开因果/恢复 gate 通过。
5. M28 无 ScopeViolation；LH09 无 scope-incompatible termination。

成本与架构：

1. logical GPT requests 总数 <=52、中位数 <=4；physical HTTP attempts 总数 <=65，并单独报告 retries。
2. 无最终 HTTP 500、stale revision、unknown evidence/reference 或 generator-consumption 错误。
3. 所有 completed Final byte-exact raw RWKV，GPT tools=0，controller_rewritten=false。
4. finalizer 只在当前 revision 全部 required obligations satisfied 后运行，action_count>=1。
5. 至少5题有真实 RWKV atom overlap；GPT 串行不降低 RWKV executor 并发。
6. 强模型 request payload 结构审计持续满足 result-only DTO；任何 process-field 泄漏直接失败。

任一质量门失败则不启动 Full90，使用完整固定结果分析全局根因。
