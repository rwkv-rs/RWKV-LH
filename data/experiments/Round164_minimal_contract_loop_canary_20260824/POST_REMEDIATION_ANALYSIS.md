# Round164 简化合同循环：修复后分析

## 结论

合同图路径现在可以收敛为一个简单闭环：强模型只编译合同和审核结果，确定性控制器只调度，
多个 RWKV 只执行原子事务，Reviewer 只接收结果胶囊。Round164 在线 Canary 证明这种简化没有
破坏证据、事务或终态一致性，并将同集强模型 logical/physical/token 成本分别降低
33.6%/35.3%/56.3%。

Round164 原始在线结果仍为 TP/FP/FN/OTHER=`8/3/3/7`，external pass=`11/21`，因此该轮
严格判定为 FAIL，没有晋级 Full90。Canary 后已修复三个通用根因中的两个确定性根因，并对
第三个 Reviewer 数值语义根因加入同调用内约束；不能把离线修复结果冒充新的在线通过率。

## 当前最小架构

1. Planner 接收 immutable request、workspace manifest、最新结果胶囊和 verdict ledger，只追加
   obligations 与 RWKV nodes。
2. 确定性 scheduler 根据依赖、scope 和 exclusive 约束选择 ready set，持久化的 execution batch
   只含 stage/revision/node identity。
3. 多个 RWKV lane 并行执行各自的 1--4 action 原子事务；强模型不接收 prompt、transcript、
   reasoning、retry 或 rejection history。
4. result capsule compiler 分别维护 content、identity、command、fact 最新视图；可执行 typed
   assertions 在本地判定，只有 semantic exceptions 进入一次 Reviewer 调用。
5. 不满足则 Planner 只接收 compact correction ledger；全部满足则 scheduler 直接放行冻结的
   read-only finalizer，由 RWKV 原样给出最终答案。

合同路径不再构造或持久化完整 `SupervisorStage`，Reviewer payload 不再传 node graph，finalizer
也不再复制全部历史 worker dependency。旧 Round149--162 stage 仅保留只读恢复兼容。

## Canary 后的系统修复

### SHA256 target pointer

`digest_equal(target_path=manifest.json, target_pointer=/sha256, source=payload.txt)` 现在比较
manifest JSON 字段值与 payload artifact digest，而不是错误比较 manifest 文件本身的 digest。
使用 Round164 B08 原始历史胶囊离线复放后，`obl_manifest_digest` 从 contradicted 变为
`satisfied`，全部 typed assertions 通过。

### Finalizer 只受合同 review 控制

finalizer 的因果条件改为“当前 graph revision 的所有 required obligations 已 satisfied”。它读取
当前已接受 workspace，不再把所有历史 correction work id 复制进 DAG。使用 Round164 M12
历史状态复放后，原始 `node_finalize` 可直接 ready，且不再需要 replacement Planner call；旧规则
要求补齐的七个 correction dependency 已记录在 replay 中。

### JSON 数值语义

Reviewer prompt 明确：JSON number 保留数值、不保留尾随小数位字符数。若用户没有要求字符串或
精确文本序列化，正确舍入的数值不能仅因 `80.0` 而不是文本 `80.00` 被否定。该项影响在线
Reviewer 行为，尚未用新的在线调用验证。

## 已验证能力

- 全测试：`177 passed`。
- Round164 21-case：runtime failure=0，artifact inheritance=0，non-content shadow=0，已完成
  transaction integrity violation=0，authoritative terminal=`21/21`。
- 104 个 minimal batches 总计 27,319 bytes，均值 262.7 bytes，无 legacy process fields。
- strong Reviewer 收到的 node/process 字段为 0。
- logical/physical/returned strong calls=`95/123/93`，总 token=`400,008`；对 Round162 同集
  分别减少 33.6%/35.3%/56.3%。
- B08 和 M12 的确定性失败路径已用同一批冻结历史数据复放通过。

## 仍然不能宣称的能力

- 不能宣称 Full90 达标；最新完整在线证据仍是失败的 Round164 21-case Canary。
- 不能保证 semantic Reviewer 零 FP。B25/M29 是 Planner 对 source-dependent output shape 的
  contract 等价性误编，M19 是 Reviewer 将 source 中 `/items` 四次误数成三次。
- 对需要条件映射、集合差、聚合计数、嵌套 shape preservation 的任务，typed assertion compiler
  尚不能全部本地执行；这些关系仍依赖一次语义 Reviewer。
- 中转站并非本轮主要根因：95 个逻辑调用中 93 个返回，失败集中在合同/语义判定，而不是 runtime
  或证据传输。

## 后续原则

不再增加新的 orchestration 层，也不把 Reviewer 变成第二个执行者。下一步质量收益应来自：

1. 扩展可执行 typed relation，使 count、key-set difference、map/filter/aggregate 与 nested shape
   preservation 尽量由本地结果编译器判定。
2. 将 Round162/Round164 中的 contract miscompile、semantic false accept、false reject 和正确
   correction 配对作为 state-tuning 数据种子；训练 RWKV 的观察、变换、验证事务，而不是训练它
   伪装成强 Planner。
3. 新的在线实验必须重新预注册固定 case、阈值和评价口径；先验证 B08/B18/M12，再决定是否
   进入新的 Full90。

## 数据来源与摘要

- 数据来源：Round164 预注册 21-case 在线 Canary 与 Round162 同 case baseline。
- 版本/用途：`rwkv-lh.round164-analysis.v1` 用于最小合同循环架构和成本验证；
  `rwkv-lh.round164-post-remediation-replay.v1` 用于修复后确定性复放。
- 生成方式：`temp/analyze_round164_minimal_loop_canary.py` 与
  `temp/replay_round164_post_simplification_fixes.py`。
- `results.json` SHA256：
  `f12b91350df173bf45ba7495b8a80f078acfa8572519428a478ba94a593e2c11`
- `GLOBAL_SUMMARY.json` SHA256：
  `7b772785a28cbdf0dfcf175ccb24bf2f0e1fa2c7ed32b735ab0f3b4e77ab9b22`
- `POST_REMEDIATION_REPLAY.json` SHA256：
  `24af5ac41d3ec366d6f90be1e8e2d570cb12eac54d65b240df0923c233702c07`
