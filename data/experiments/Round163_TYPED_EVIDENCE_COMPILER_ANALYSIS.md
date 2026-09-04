# Round163：Typed Evidence Compiler 整改分析与当前能力边界

日期：2026-08-24

## 结论

当前实现已经形成“强模型低频计划/审核、RWKV 高频并行执行”的闭环架构，并清除了
Round162 中最确定的四类控制器误判：DSL 语义错编、action-artifact 串线、同路径证据视图
互相覆盖、无变化纠错仍重复调用强模型。完整测试为 175 passed；Round162 的 90 例离线
重放门槛全部通过。

但本轮没有重新运行在线 Full90，因此不能声称新的 TP 已经超过历史结果。最近一次在线、
同口径、完整 90 例证据仍是 Round162：TP/FP/FN/OTHER=`14/3/21/52`。Round163 证明的是
控制器确定性缺陷已被清除以及错误完成更严格地 fail-closed；实际净收益必须由独立在线
canary/Full90 验证。

## 已完成的架构修改

1. typed contract 增加 kind-specific 可执行语义检查和显式 `semantic_review`。现有 DSL 不能
   完整表达的 multi-source transformation、非 JSON pointer、unsupported aggregate、无真实
   placeholder template 不再返回机械 false，而是只交给强 Reviewer。
2. result capsule 严格按 action_id 绑定 artifact。多 action atom 中无 artifact 的 action 不再
   继承整个 atom 的 artifacts。
3. latest evidence 从单一 path 改为 content、identity/digest、command、fact 多视图。write/check/
   digest receipt 不再冒充目标文件内容；mutation 会使旧 content 失效，直到 RWKV 再次读取。
4. correction signature 去除 correction node id、patch id、自然语言 error message 等非状态量，
   加入 contract contradiction、execution failure、evidence insufficient 恢复分类。证据不变时
   在下一次强 Planner 调用前 bounded stop。
5. 多操作 mutation transaction 必须包含 read-only verifier，而且最后一次 mutation 后必须有
   成功的目标范围 read/digest/check；否则 RWKV Final 不构成 node completed，workspace 不提交。
6. resume 的 `run_started` 明确记录被替代的历史 terminal event；历史事件不删除，但当前只存在
   一个权威终态。
7. contract scheduler 给通用 stage validator 只投影成功 dependency handoff。早期失败仍作为
   capsule 给 Reviewer，但不会在 frozen obligations 已满足后错误阻止 finalizer；这修复了
   Round162 B11 的通用 runtime 根因。
8. 强 Planner prompt 明确偏好一个 RWKV state 内 2–4 action 的小事务；强 Reviewer 只接收
   public result capsules，不接收 RWKV prompt、推理、重试和中间过程。

## 固定离线结果

来源、版本、用途、生成命令和 SHA256 见
`Round163_typed_evidence_compiler_offline/MANIFEST.json`。

- 90/90 audit、342 typed assertions 完整重放。
- Round162 已知 42 个不可执行 assertion：42/42 进入 semantic exception/unresolved。
- 重放结果：local passed 172、local contradicted 43、unresolved 127；本地可确定处理
  215/342（62.9%）assertion，其余由 Reviewer 或新证据处理。
- raw action capsules 499，typed latest capsules 153；artifact 错绑 0，非 content shadow 0。
- Round162 93 个 correction signatures 原本 93 个全不同；新规则会在 36 例、76 次 stagnant
  review 后阻止再次无效规划。
- resume 历史原始 exactly-one terminal 为 88/90；按 supersession 后权威终态为 90/90。
- 新 transaction integrity 会拒绝 18 个历史“写后未观察却报完成”的 node。这会降低错误完成，
  但也要求 RWKV 真正保留最后一个 action 做验证。
- 全量代码回归：175 passed，0 failed。

## 当前能做到什么程度

### 工程上已经具备

- 强 Planner 一次编译 immutable request、typed obligations、依赖图和 scoped RWKV transactions。
- 最多四个无写冲突 RWKV atom 并行执行；RWKV 是唯一工具参数生成者和工具操作者。
- text/JSON 文件读写、复制、精确替换、摘要、命令检查、依赖 handoff、持久化恢复和最终
  RWKV 原文输出。
- 62.9% 的历史 assertion 可由本地 public-result checker 直接判定，不需要强 Reviewer；复杂
  语义只把结果而非过程发给 Reviewer。
- 证据不增长时及时停止，避免用反复 Planner/Reviewer 调用掩盖 RWKV 或 contract 的真实问题。

### 最近在线实测所支持的上限

Round162 仍是当前唯一经过完整在线 Full90 验证的版本：

| 层级 | strict TP | external 实际通过 | 总数 |
|---|---:|---:|---:|
| B | 7 | 22 | 30 |
| M | 6 | 11 | 30 |
| H | 1 | 2 | 18 |
| LH | 0 | 0 | 12 |
| 合计 | 14 | 35 | 90 |

53 个成功拿到计划的 case 中有 35 个 external pass（66.0%），说明 RWKV 在有明确小事务时
经常能生成正确 artifact；但旧控制器只正确完成 14 个，主要损失发生在 contract/evidence/
correction/acceptance，而不全是 RWKV 工具执行能力。

### 尚未证明或仍然不足

- 强模型中转在 Round162 有 37/90 plan unavailable；Round163 不能修复外部 relay 可用性。
- 复杂多源选择、递归合并、业务条件、精确聚合仍依赖 semantic Reviewer；本地 DSL 不再假装
  会算，但 Reviewer 仍可能误判。
- Round162 的 3 个 FP 都来自错误 contract/semantic acceptance。新增显式 semantic boundary
  会减少错用机械 checker，但不能证明强 Reviewer 的 FP 已归零。
- H/LH 尚无足够在线成功证据；现在适合做文件/JSON/代码类的分解执行器，还不能称为稳定的
  通用 long-horizon agent。
- 新 transaction gate 更严格，若 RWKV 把 action budget 全花在读取或写入而没有后置验证，
  case 会安全中断。因此下一轮数据/训练应重点训练“inspect -> mutate -> verify -> Final”的
  state trajectory，而不是继续堆 Planner 规则。

## 下一次在线验证建议

先预注册包含以下共同根因的固定 canary：42 个 semantic pattern 的代表、9 个 evidence shadow、
7 个 artifact inheritance、18 个 transaction integrity 历史 node、B11 finalizer runtime，以及
3 个旧 FP trap。canary 通过后再以相同代码和阈值跑 Full90。在线指标继续使用既有 external
TP/FP/FN/OTHER，不调整 checker；同时比较 GPT logical/physical calls、tokens、stagnant stop、
strict TP 和 FP。
