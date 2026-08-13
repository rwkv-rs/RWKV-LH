# Round37 observed artifact metadata 定向分析

## 结果

- B08：Strict PASS
- B19：External PASS、Agent blocked
- 两题最终 `manifest.json` 的 sha256 都与真实 `sha256sum payload.txt` 完全一致。

## 证据链

### B08

T1 `read_file` 的 persisted ArtifactRecord sha256 为 `6f224b6a...c9d05`。Round37 action capsule 将该值作为 `observed_artifacts` 展示；T2 的 RWKV action 自行选择 `write_json` 并把同一值放入 manifest。T3 的再次写入也保持该值，T4 先读取 manifest，后选择 `run_command sha256sum payload.txt` 做独立检查。最终 Strict PASS。

Controller/capsule builder 没有把 digest 写入 action 参数；action event 中的 value 全部来自 RWKV 响应。

### B19

T1 observed sha256 为 `799964b9...0c6a`；T2/T3 的 RWKV write_json action 与最终 manifest 都使用同一正确值。External 因而从 Round36 FAIL 变为 PASS。

Agent 阻塞发生在 T4“Verify digest against payload.txt bytes”。RWKV 连续选择 read_json(manifest.json)，局部 postcondition 正确指出仅读取 manifest 不能独立验证 payload bytes；unchanged-observation suppression 重用同一 replan，recovery budget 耗尽。该失败是规划/动作策略冗余，不是 digest 接口或内容错误。

## 结论

Round37 用完整真实工具 observation 消除了 B08/B19 的 hash 幻觉与假阳性，没有替 RWKV 生成 action 或判定。B19 仍需由后续最小规划/工具选择结构减少重复验证 Task；不能把正确 External 结果强行改成 Agent completed。
