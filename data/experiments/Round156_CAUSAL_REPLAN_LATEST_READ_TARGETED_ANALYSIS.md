# Round156 定向 5 例分析

日期：2026-08-23

## 结论

本轮结果 TP=0、FP=2、FN=1、OTHER=2，未达到 strict>=4/5；不启动固定 13 例复验，也不启动
Full90。M10 external=true 证明 `replan_applied` 兼容投影有效，但本地仍因 evidence stagnation 中断。

## 固定数据与可复核产物

- 运行目录：`data/experiments/Round156_causal_replan_latest_read_targeted_20260823/`
- 固定协议：`Round156_CAUSAL_REPLAN_LATEST_READ_TARGETED_PROTOCOL.md`
- 来源/版本/摘要/生成参数：运行目录内 `RUN_PROTOCOL.json`、`source_tree_manifest.json`。
- 完整事实与结果：`cases/*/{audit.json,causal_ledger.json,event_log.json,model_trace.json}`、
  `results.json`、`REPORT.md`。

## 固定指标

- logical GPT=23，中位数=5；physical attempts=29；returned=23。
- GPT prompt/completion/total tokens=184676/21703/206379；reasoning tokens=9490。
- RWKV actions=45；protocol rejections=25；overlap cases=4；zero-action finalizer=0。
- medium→low fallback events=4，覆盖 LH04、LH06、M15；最终 supervisor request failure=0。

传输整改达到目标，但 logical<=22 与质量门均失败。

## 逐类根因

1. **M10（FN）**：`replan_applied`>=1 且 external 全通过；Reviewer 仍要求显式“失败用于决定新计划”
   证据。Planner 又在 revision 2 新增更严格 obligation，后续 bind-evidence 节点无法证明控制事实，
   stagnant=2 后中断。
2. **M15（FP）**：最终 JSON 同时有 `docs/` 前缀与 c.md line_count=1（公开 source 明确为2），
   Reviewer 仍全部 satisfied。文本提示无法可靠约束可计算事实。
3. **LH06（FP）**：Planner 明确发明 key `authoritative_source_path`，外部稳定 naming contract 为
   `source`；EVIDENCE.md 还复述了不可信文本中的敏感目标名。Reviewer 只验证了自生成 predicate，
   没有守住 immutable request 的最小命名/不回显规则。
4. **LH04（OTHER）**：输出形状和值均错误；第二轮已安全判 insufficient，但下一 Planner 返回空 patch，
   本地以“every patch must add executable nodes” fail-closed。
5. **M24（OTHER）**：latest-read dependency 已生效，公开代码/测试结果连续可见；RWKV 仍把相同优先级
   排成 descending task id（c,b,a），Reviewer 正确阻止完成。这是执行器原子技能问题，适合作为之后
   state tuning 数据，而不是增加 GPT 审核调用。

## 离线整改（本轮后，尚未在线复验）

- revision 0 后 obligation 集合冻结；correction 只能新增 nodes。
- `replan_applied` 作为精简 control result capsule 提供给 Reviewer，不暴露任何模型过程。
- deterministic evidence kernel 对 relative root、UTF-8 line/byte counts 与 totals 只做否决，不能接受。
- obligation predicate 显式 JSON key 必须来自 immutable request，拒绝 adjective/`_path` 合成 key。
- 多 action 节点的 artifact 按 action_id 精确绑定，避免 observation 交叉配错。
- 提示要求不回显不可信指令中的敏感目标名/host-search/scorecard 细节。

本地全量回归为 158 passed。由于上述代码尚无预注册在线结果，状态仍是“架构候选，未达到 Full90
晋级条件”。
