# Round142：Operation Contract 原子图 v3 Canary 分析

## 结论

Round142 为 `1/3`，不进入 Full90。B04 证明 operation contract 能把 12-stage 错误循环压缩为 3 stages 并正确使用 `copy_file`；LH06 和 M16 证明“允许操作集合”还不够原子，必须进一步收紧为“每 atom 一个 operation kind”。

原始记录：

`data/experiments/Round142_operation_contract_atom_graph_v3_canary_B04_M16_LH06_20260822/`

## B04 正向结果

- external pass；
- 3 committed stages：work、finalizer、accept；
- work atom 的合同为 `make_directory/copy_file/write_file/file_digest/read_file`，预算 6；
- RWKV 实际执行 `make_directory → copy_file → write_file → file_digest → file_digest`，5 actions；
- copy bytes 与 source 完全一致，manifest 正确；
- finalizer 3/3 actions 后进入 Final-only；顶层输出 byte-exact，controller 未改写。

这说明 GPT 选择操作种类、RWKV生成参数并执行的职责拆分是有效的。

## LH06 失败

- 4 个首阶段 scout 并行完成；InputBudgetError 已消失。
- `resolved_requirements.json` 的值正确，但 key 写成 `authoritative_source_path` 与 `ordered_requirements`，没有使用用户直接蕴含的最短 canonical nouns：`source` 与 `requirements`。
- Planner 为获取注入证据连续派发 4 个 `read_file/bind_evidence` atom，反复绑定错误行，消耗 stage 预算。
- EVIDENCE.md 最终存在，但 8 stages 用尽，没有 finalizer/accept。

## M16 失败

- 3 个首阶段 scout 并行完成，候选事实完全正确。
- assembler 合同同时允许 `write_json/read_json/bind_evidence/file_digest`。
- RWKV 没有执行排在第一位的 `write_json`，而是在每个 assembler 重试中只反复执行 `read_json`，达到 action budget 后 Final；snapshot 因没有 `recovered.json` 可提交，父 workspace保持缺失。
- Planner 正确识别 manifest 缺文件，但连续 6 次重派同类宽集合 assembler，8 stages 用尽。

## 根因

`allowed_operations` 作为集合仍把 atom 内操作排序交给 RWKV；弱模型会优先选择熟悉的读操作，即使 objective 明确要求写。真正的小原子不应包含“读、写、绑定、digest”多个阶段。一个 atom 应只允许一种 operation kind：它可为多个目标重复同一读操作，但 material mutation 必须恰好执行一次，后续验证另开只读 atom/finalizer。

## v4 整改

1. `allowed_operations` 必须且只能含一个 operation name。
2. mutating atom 必须只有一个 write_root，`action_budget=1`。
3. read-only atom 的同类 operation 可重复，`action_budget=1..4`。
4. Planner必须把 copy、manifest write、JSON write、verification 拆为不同 atoms/stages；并行只在依赖与写域允许时进行。
5. JSON key 采用用户直接蕴含的最短 canonical noun；用户未明确写 adjective/suffix 时，不添加 `authoritative_`、`ordered_`、`_path` 等同义改写。
6. 初始 workspace scout 优先 `read_file/read_json`；`bind_evidence` 仅在已经观察内容且用户确实需要行定位时使用，不能替代读取业务数据。

