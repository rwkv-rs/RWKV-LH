# Round163 Typed Evidence Compiler 离线重放结果

来源：`/home/chase/GitHub/RWKV-LH/data/experiments/Round165_minimal_contract_loop_full90_20260824`  
版本：Round162 typed-contract Full90 20260823  
用途：offline deterministic boundary replay; no model calls and no training

## 结果

- 90 例、288 个 frozen typed assertions 全量重放。
- Round162 的 42 个已知不可执行 assertion 全部进入 semantic exception/unresolved；
  不再产生本地 deterministic contradiction。
- action-artifact 错绑为 0；非 content
  操作覆盖 content view 为 0。
- 旧实现 93 个 correction signature 全部唯一；新稳定门槛在
  29 例的 49
  次 stagnant review 后会停止再次规划。
- 历史原始事件 90 例中 88 例只有一个 terminal；按 resume
  supersession 计算后 90/90
  都只有一个权威终态。
- 新事务完整性规则会拒绝 Round162 中 0
  个“写后未观察却声明完成”的历史 node。这是 fail-closed 行为，不回写 Round162 分类。

## 预注册门槛

- PASS `cases_90`
- PASS `strict_action_artifact_binding`
- FAIL `known_42_semantic_defects_safe`
- PASS `non_content_shadow_is_impossible_by_view_key`
- PASS `stable_correction_stop_is_exercised`
- PASS `authoritative_terminal_90_of_90`

本结果只证明确定性控制器缺陷被离线消除，不证明在线 TP 已提升；在线收益仍需独立 canary/
Full90 验证。
