# Round37 预注册协议：完整投影真实 artifact observation

## 触发证据

Round36 的 B08、B19 都在 T1 `read_file(payload.txt)` 后要求生成真实 SHA256 manifest。运行时 ActionResult 已记录：

- artifact relative path；
- 由 Harness 对真实文件字节计算的 sha256；
- media type 与 size（ActionResult 中）。

但 `rwkv-lh.action-commit-capsule.v1` 的 dependency observation 只包含文本 content 与 pagination metadata，没有投影任何 artifact digest。RWKV 因而自行生成错误 SHA256；write verifier 再以该错误 action 参数为 expected，最终两题 Agent completed / External FAIL。

## 单一结构变更

在 action、Task-postcondition、recovery 的 phase observation 中，对 MemoryEntry 已绑定的 `artifact_refs` 增加只读 `observed_artifacts`：

```json
[{"path":"payload.txt","sha256":"...","media_type":"text/plain"}]
```

字段全部来自 RunState 中已持久化的真实 ArtifactRecord。保持 dependency content 与 pagination metadata；不投影内部 artifact id、absolute path、状态机字段或 schema audit 对象。

## 明确禁止

- capsule builder 不重新计算 hash，不读取隐藏验收，不生成 manifest value。
- 不按 Task 关键词选择是否展示；所有有 artifact_refs 的 phase observation 采用同一投影。
- 不替 RWKV 选择 write_json/check_command，也不复制 digest 到 action 参数。
- 不用 observed sha256 自动判断 Task/Goal pass，不修改 workspace 或最终回答。
- Round37 不改格式别名、工具 schema、规划、recovery 或 evidence commit。

## 固定验证

1. 单元测试：artifact ref 存在时，relative path、sha256、media_type 出现在 phase capsule；absolute root、artifact id 不出现。
2. 单元测试：unknown artifact ref 不补造记录；content 与 pagination metadata 保持。
3. 全量 pytest、LH-Control 30/30、E2E-90 validate-only 90/90。
4. 真实 canary：B08、B19。检查 RWKV 是否原样使用 observed digest、External/Strict、FP，以及 action/Goal chain。
5. 若模型仍不用 digest，不在本轮增加规则强制复制。

## 成功判据

- RWKV 能在 prompt 中看到此前已真实存在但丢失的工具 observation。
- builder 没有生成语义值或修改模型输出。
- 两个 hash canary 的实际 manifest digest 与 observed artifact digest 可追溯一致。
- 离线回归无退化。
