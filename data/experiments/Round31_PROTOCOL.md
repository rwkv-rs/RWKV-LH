# Round31 预注册协议：紧凑因果 provenance commit

预注册日期：2026-08-13。依据为 Round30 E2E-B02 的 14 请求完整链。Round31 请求尚未发出。

## 同一结构整改

`criterion_evidence_commit.compact-causal.v1` 同时移除三个属于同一固定接口的冗余障碍：

1. criterion commit 没有工具选择，改用单一 JSON decision contract：顶层只有 `decision`、`bindings`，不再要求模型重复固定
   `commit_criterion_evidence` 名称。raw JSON 仍由模型自己生成，不由 normalizer 包装。
2. binding 的判定字段固定为 `criterion_id/actual_ref/expected_ref`；`reason` 允许模型选择性提供，但不再作为 ref 校验的前置
   条件。缺失时不生成解释文本，内部 `rwkv_reason` 保持空值。
3. actual catalog 扩展为当前 Task observation 加已完成声明依赖的 observation；每个 source 保留 owner Task、dependency path、
   artifact/path/digest。未知 Task、非祖先、未完成 Task 和无审计 observation 仍不可选。expected catalog 与每个 binding 的
   same-ref/path-lineage independence 检查保持不变。

Controller 仍要求 bindings 精确覆盖 RWKV 在上一请求选择的 criterion ids，并整体接受或整体拒绝；不会删除错误 binding、选择
正确子集、修改 ref 或根据 external verifier 生成证据。

## 固定验证

- JSON parse/contract 第一次失败、第二次由 RWKV 自己修正；不得再出现 None dereference。
- 有/无 optional reason 都保留模型原始字段；缺失 reason 不补文本。
- direct/transitive completed dependency 可作为 causal actual；非祖先、inactive、unfinished、同 path actual/expected 全拒绝。
- 完整 pytest、LH-Control-30、E2E-90 validate-only。
- 同一 E2E-B02 real canary。必须逐项检查 T1 过早 GC2 claim、T2 三个 refs、Strict/External/FP/FN、最终 raw 输出和 Codex
  reference similarity；即使 Strict PASS，也不能把 T1 的语义误判归为结构正确。
