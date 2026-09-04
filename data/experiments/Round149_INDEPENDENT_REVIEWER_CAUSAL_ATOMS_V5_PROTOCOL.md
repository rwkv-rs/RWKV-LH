# Round149：Independent Reviewer + Causal Atoms v5 Canary 预注册

> 状态：**未执行，已在运行前废止**。该固定 stage-loop 方案由
> `Round149_CONTRACT_GRAPH_RESULT_CAPSULE_CANARY_PROTOCOL.md` 的 Contract Graph 双循环替代；
> 本文件只保留架构演进记录，不作为任何结果的预注册口径。

日期：2026-08-22

## 唯一架构整改集合

1. terminal `accept_final` 必须经过独立 GPT-5.4 evidence Reviewer；Planner 与 Reviewer 分离。
2. finalizer 在同一 atom 内至少执行一个已承诺 read/check action，过早 Final 不产生新业务 stage。
3. child atom actions 带 provenance 投影进父因果账本；失败后新 dispatch 登记真实 replan。
4. 标记为 process-loss 的异常穿透 pool，并从同一 atom store/workspace 恢复。
5. path mutation 可声明一至两个 roots（支持 move source+destination）；exclusive external side effect
   不需要伪造 path root。
6. GPT 请求跨 case 串行化、transport retry=3、semantic repair=2；RWKV atom 并发仍为4，不降低。

不修改任务、hidden verifier、评分算法、RWKV sampling 或 Final 非干预原则。

## 固定 canary

- 旧 FP 公开证据检查：B22、M15、LH06。
- 终止/FN：B09、M24。
- 因果/恢复/scope：H09、M10、LH04、LH08、M28、LH09。
- 稳定正例：B04、M16。
- 共 13 例；case concurrency=4，atom concurrency=4，max stages=8，max transitions=200。

## 成功门

- strict 至少 11/13；B09、M24 至少一题由 FN 转 TP，且无新增 FN。
- B22/M15/LH06 至少两题由 FP 转 TP；H09/M10/LH04/LH08 至少两题的公开因果/恢复门通过。
- M28 无 ScopeViolation；LH09 无 scope-incompatible planner termination。
- 无 finalizer action_count=0；无 HTTP 500 终止、duplicate id/empty disposition 等语义终止。
- mutation atom operation contract 全部满足；process-loss snapshot 不直接提交父 workspace。
- 所有 completed Final byte-exact raw RWKV；GPT action count=0；至少 5 题实际并行。

未通过则不启动 v5 Full90，按固定结果继续根因分析。
