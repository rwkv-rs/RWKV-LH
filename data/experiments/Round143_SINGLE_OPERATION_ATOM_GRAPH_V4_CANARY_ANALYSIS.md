# Round143：Single-Operation Atom Graph v4 Canary 分析

## 结论

Round143 为 `1/3`，不进入 Full90；但三题均证明 single-operation 架构方向成立。

- B04：external pass、completed，4 stages；首 stage 两个 RWKV mutation atoms 实际并行，每个 mutation 恰好 1 action。
- LH06：业务产物 external pass，但 8 stages 后 interrupted，原因是 Reviewer 对已经满足请求的 EVIDENCE.md 连续风格/措辞重写，没有及时 accept。
- M16：5 stages completed 并被接受，但 JSON item 对象额外包含 `source` 字段，external fail。

原始记录：`data/experiments/Round143_single_operation_atom_graph_v4_canary_B04_M16_LH06_20260822/`

## 已验证

1. Mutation 原子均为单 operation、单 action；没有工具漂移和长循环。
2. M16 形成并行读取 → 单次 write_json → 单次 read_json verifier → finalizer → accept 的正确图。
3. LH06 形成 4-way parallel read → 2-way parallel write，且 `resolved_requirements.json` 精确使用 `source`、`requirements`。
4. InputBudgetError、failed snapshot 污染和宽工具循环均未复现。

## 剩余根因

### 证据优先级

Planner仍把 RWKV `candidate_output` 当成事实，而不是把 successful action result 与 workspace artifact 作为权威观测。LH06 scout summary 中存在错误概括，导致 Reviewer反复改写本来已能通过外部校验的 EVIDENCE.md。

### Nested shape 不够精确

M16 writer objective说明了顶层 `items` 与 `sources`，但没有声明 item 对象恰好只有 `id`、`value`。RWKV把 provenance 同时写入 item.source 和顶层 sources。Verifier也只检查顶层键，导致错误 acceptance。

## Round144 全局整改

1. successful action result/arguments 与 artifact/manifest 是观测事实；candidate summary 只是可疑摘要。
2. 每层嵌套对象都要声明 exact key set；已有独立 provenance mapping 时不得在 item 内重复 provenance，除非用户明确要求。
3. finalizer读取当前产物并且没有具体观测矛盾时应 accept；不得为了风格、细节或同义措辞继续重写。

