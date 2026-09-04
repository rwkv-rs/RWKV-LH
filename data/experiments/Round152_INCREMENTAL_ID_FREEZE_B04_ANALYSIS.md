# Round152 Incremental ID Freeze B04 分析

日期：2026-08-23

## 结论

Round152 **FAIL（FP）**。existing-ID 修复有效，运行无 unknown-reference，且只使用初始 Planner + 一次
Reviewer 两个逻辑强模型调用；但 RWKV 把 manifest 写成 `archive/source.txt\n`，Reviewer 错误接受，
最终 agent completed=true、external=false。

原始目录：`data/experiments/Round152_incremental_id_freeze_B04_20260823/`。

## 证据

- Planner 2 个物理 attempts 后返回；Reviewer 1 个 attempt 返回；无 semantic repair。
- 6 个 work atoms、7 actions、0 protocol rejection，Final byte-exact raw RWKV。
- source 和 destination digest 均为 `40c095...af16`，copy byte equality 正确。
- `archive/manifest.txt` exact read 为 `archive/source.txt\n`，hidden verifier 要求
  `archive/2026/source.txt\n`。
- Reviewer 明知 exact observation 为前者，仍称其为 required relative path，属于公开 request 可判定的
  acceptance 错误。

## 根因与整改

1. Planner predicate 把 exact path 降格为模糊的 “required relative path”，削弱 obligation 的字面锚。
2. 为缩短初始 graph latency，Round151/152 把 Planner 和 Reviewer 都设为 low reasoning；Planner 可低，
   但 Reviewer 的精确矛盾检查不应同步降级。

下一轮保持常规逻辑调用数 1+1，分离 reasoning：contract Planner=low、Reviewer=medium；Planner prompt
要求 predicate 保留相关 exact literals，Reviewer恢复通用 destination-relative-path 解释规则。
