# Round22 既有聚合分析器校正记录

## C01：B09 action-choice 被错配为 tool-action

### 原聚合逻辑

`temp/analyze_round22_blind_lifecycle_and_snapshots.py::action_materialization_failures` 遇到
`model_protocol_blocked(phase=action_materialization)` 后，选择同一 task 的“最后一次 tool_action request”，
而没有沿 block 前驱 error 的 `request_id/request_type` 连接。

### 逐事件核对

E2E-B09：

1. `MR-c9807ca3e8ea4475` tool_action 输出合法 `{name:"read_json", arguments:...}`，经过
   `model_protocol_normalized`，event 29 已 `action_selected=read_json`；它不是失败请求。
2. 后续 recovery 的 tool_choice：`MR-c8b6fb...` 选择不存在的 `read_csv`，触发一次 contract error；
   第二次 `MR-7a9b1b...` 选择不存在的 `read_text`。
3. event 46 是 `model_contract_error(request_type=tool_choice)`；event 47 才是
   `model_protocol_blocked(message=unsupported action type: read_text)`。
4. 原脚本把 event 47 错连到较早已成功的 `MR-c980...` tool_action。

### 修正影响

- Round22 真正 action-argument/materialization block：`36`，不是原聚合的 `37`。
- snapshot-exposed action block 仍为 `29/192`（`15.10%`）。
- non-snapshot action block 应为 `7/387`（`1.81%`），不是 `8/387`（`2.07%`）。
- 另有 action-choice block `1` 题（B09），必须单列。

该校正只修事件关联，不改变原始事件、模型输出、workspace、评分或 Round22 冻结结果。后续人工审阅
以 error event 的真实 `request_id/request_type` 为权威，不使用“同 task 最后请求”近似。

## C02：B04 正确 target 被覆盖被误记为 false

### 原聚合结论

`POSTSTANDARD_STAGE_ATTRIBUTION.md` / `poststandard_stage_attribution.json` 将 B04 的
`correct_target_was_overwritten` 记为 `false`，并称没有可直接从 write action 与 acceptance 对比确认的案例。

### 逐事件与字节核对

1. event 49 的 T4 tool-action raw 为 `write_file(archive/manifest.txt, "archive/2026/source.txt\n")`。
2. event 55 snapshot 记录 SHA-256=`6c5611...`、size=24；这与 acceptance 要求的标准字节完全一致。
3. event 165/168 的 T8 raw 选择 `write_json`，value 仍是语义字符串 `archive/2026/source.txt\n`。
4. event 174 snapshot 已变为 SHA-256=`f1e4d7...`、size=28；实际字节是
   `b'"archive/2026/source.txt\\n"\n'`，即 JSON 引号和转义被写入文件。
5. 两次 action 的 path 完全相同，且中间没有外部修改；因此这是可直接证明的 RWKV 后续写覆盖正确 target。

### 修正影响

- B04 必须记为 `correct_target_was_overwritten=true`。
- 首个产物错误不是初次 producer 写错，而是 T8 验证 task 的错误 mutation。
- action-derived `json_field_equals` 虽通过，只能证明 JSON action 与自身参数一致，不能证明 Goal 所需的原始
  文件表示正确。

该校正暴露的是分析器没有按同一路径重建 artifact 字节时间线。后续人工审阅必须逐个 target 对照每次 write
后的 hash/bytes 与 acceptance，不能只按 action 类型或最终 workspace 归类。
