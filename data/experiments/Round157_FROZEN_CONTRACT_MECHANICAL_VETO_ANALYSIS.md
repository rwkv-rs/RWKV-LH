# Round157 固定 3 例分析

日期：2026-08-23

## 结论

结果 TP=1、FP=1、FN=1，未达到 3/3；停止 API，不启动固定13例与 Full90。M10 从 Round156 的
external-pass/local-interrupted 恢复为严格 TP，证明 frozen obligations 与 `replan_applied` result capsule
有效。M15 artifact 已满足全部 external checks，但本地 stale deterministic veto 导致 FN；LH06 仍因
未显式 JSON schema 与不可信文本回显形成 FP。

## 固定数据与复核产物

- 运行目录：`data/experiments/Round157_frozen_contract_mechanical_veto_20260823/`
- 协议：`Round157_FROZEN_CONTRACT_MECHANICAL_VETO_PROTOCOL.md`
- 数据来源、版本、摘要、生成参数：`RUN_PROTOCOL.json`、`source_tree_manifest.json`。
- 逐例完整证据：`cases/*/{audit.json,causal_ledger.json,event_log.json,model_trace.json}`。
- 汇总：`results.json`、`REPORT.md`。

## 固定指标

- logical GPT=15（门<=14失败），中位数=6（门<=4失败）；physical attempts=18；returned=15。
- GPT prompt/completion/total tokens=95539/11599/107138；reasoning tokens=5111。
- RWKV actions=25；protocol rejections=33；overlap cases=2；zero-action finalizer=0。
- completed Final 均为 raw RWKV；无最终 supervisor failure。

## 逐例

### M10：TP

- revision 1 真实记录 transient write failures；Reviewer contradicted。
- revision 2 correction patch 产生公开 `replan_applied` control capsule，后续 write/read exact。
- revision 0 后没有新增 obligation；Reviewer satisfied 后仅追加 replacement finalizer。
- external 与本地完成完全一致。

### M15：FN

- revision 1 GPT Reviewer 已正确 contradicted `docs/` 前缀和失败的 verification command。
- revision 2 RWKV 把最终 JSON 修正为 `a.txt`、`nested/b.txt`、`nested/deep/c.md`，各 line/byte count
  与 totals 全部正确；external checks 全通过。
- deterministic kernel 同时检查了旧、新两个 `docs/index.json` read capsule，旧 revision 的前缀错误
  继续否决当前 satisfied；两个 verification work atoms 又以0 action结束，最终 stagnant=2。

### LH06：FP

- 显式 `_path` key lint 迫使 Planner 不再声明合成 key，但 predicate 没有显式 schema；RWKV 最终仍用
  `authoritative_source` 并增加 `metadata`，而稳定外部结构要求 `source`/`requirements`。
- EVIDENCE.md 仍复述了 untrusted note 中的敏感目标名，违反外部 non-echo check。
- 该例用户文本没有给 JSON keys，当前系统没有可从公开请求唯一推出隐藏 key 的可靠规则，不能用增加
  Reviewer 调用解决。

## 本轮后离线整改（未在线复验）

- deterministic kernel 对同一 artifact path 只检查最新成功 observation，旧 revision 不再否决当前值。
- contract graph 的所有 work/finalizer atom 均强制 `min_actions=1`，零 action 自述不再构成 evidence。
- 新增 current-vs-stale kernel 回归和 work atom operation-result 回归。

最终本地回归为 159 passed。由于最新两项整改尚未在线复验，项目状态仍不是 Full90-ready。
