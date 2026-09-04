# Round155 固定 13 例分析

日期：2026-08-23

## 结论

本轮未通过预注册质量门，不启动 Full90。结果为 TP=4、FP=3、FN=0、OTHER=6；相对 Round154
的 3/5/1/4，B22 从 FP 恢复为 TP，旧 FP 中 LH09、M16、M28 被 mandatory gate 正确阻止，
但 LH04、M15 与 M10 仍发生假完成。

## 固定数据与可复核产物

- 运行目录：`data/experiments/Round155_mandatory_contract_parent_exclusive_canary_20260823/`
- 固定协议：`Round155_MANDATORY_CONTRACT_PARENT_EXCLUSIVE_CANARY_PROTOCOL.md`
- 数据来源/版本/用途/摘要：运行目录内 `RUN_PROTOCOL.json`、`source_tree_manifest.json`。
- 逐例事实：`cases/*/audit.json`、`causal_ledger.json`、`event_log.json`、`model_trace.json`。
- 汇总：`results.json`、`REPORT.md`。
- 生成方式：固定 runner、13 个预注册 case、concurrency=4、full tool disclosure、GPT 串行，参数见协议。

## 固定指标

- logical GPT calls=37，中位数=2；physical attempts=53；returned=32。
- GPT prompt/completion/total tokens=189780/24111/213891；reasoning tokens=10182。
- RWKV actions=55；protocol rejections=20；存在真实 overlap 的 cases=4。
- completed Final 均为 exact raw RWKV；zero-action finalizer=0；result-only DTO 未发现 process field。

成本门 logical<=52、physical<=65 达到，但并发门（至少5例 overlap）与质量门失败。

## 根因

1. **mandatory gate 修复有效**：Planner 不再能用 `required=false` 绕过 Reviewer；LH09、M16、M28
   不再 FP。B22 的 checkbox predicate 也使原 FP 转 TP。
2. **medium Planner 网关不稳定**：LH06、LH08、LH09、M16、M28 的初始 plan 均连续三次 HTTP500，
   完全没有 RWKV action。重复相同请求不是有效 retry。
3. **prose path 校验根因已修复**：Round154 的 M15/LH04/M24 `before/after`、`TaskQueue.pop` 等
   误判未再出现；但 M15/LH04 转为真实 Reviewer FP。
4. **exclusive snapshot 根因已修复**：独占 command 不再因临时 workspace 提交机制静默丢副作用；
   M28 失败来自选择/修正未完成，而不是 effect 消失。
5. **Reviewer 对机械事实不可靠**：M15 把带 `docs/` 前缀的 path 误称为 relative；LH04 接受了
   与外部 JSON container key 不同的 `entries`；M10 完成恢复但没有历史兼容 `replan_applied` 事件。
6. **correction writer 缺当前内容**：M24 后续 writer 未依赖最新 queueing.py read，反复整文件重写并
   丢失 `add` 或写错 heap tie-break；这是 RWKV dependency 数据缺失，不是 GPT 调用次数不足。

## 后续整改（Round156 前）

- Planner 5xx physical retry 自动 medium→low。
- 增量 contract patch 投影 `replan_applied`。
- 改写现有内容必须直接依赖最新成功 read。
- 强化相对扫描根与 immutable-request 优先的 Reviewer 规则。

这些整改必须先经定向预注册验证，不能据此直接运行 Full90。
