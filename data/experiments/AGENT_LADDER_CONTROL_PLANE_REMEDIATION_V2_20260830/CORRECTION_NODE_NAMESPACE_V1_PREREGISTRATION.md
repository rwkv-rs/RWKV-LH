# Correction Node Namespace V1 预注册

## 已冻结问题

- 来源运行：`run_s66_g3_g6_post_lean_contract_v1/results.json`。
- 来源 SHA256：`196cf691f1c6babe213dd05f7ed8e9c7aa4e149b5e26903f49327d13b3921778`。
- 10 题中 4 题的第一个阻断错误完全相同：`graph patch cannot redefine an existing node`。
- 原始强模型响应、RWKV 输出和来源运行只读保存，不做修复、覆盖或删除。

## 根因假设

节点 ID 是图存储的机械标识，不是 Planner 的业务语义。当前 correction 严格 schema 只约束 ID 字符集，没有编码当前 graph revision 的新鲜命名空间；强模型因此可在结构化响应内复用现有 ID。追加图随后正确拒绝冲突，但语义 repair 提示不能结构性消除该错误。

## 单一整改

为 `graph_revision > 0` 的 contract-plan v7 JSON schema 动态生成一个确定性、与全部现有节点前缀不相交的 ID namespace，并把 `new_nodes[].atom.atom_id.pattern` 限定到该 namespace。

- 不改写 Planner 响应。
- 不在响应后重命名节点。
- 不改变任何依赖、目标、路径、工具或参数。
- 初始图 ID 契约保持不变。
- append-only 图校验保持不变，仍是最终权威。

## 固定验证

1. 单元测试：初始 schema 不变；correction/finalizer schema 的 atom ID pattern 与所有现有节点不相交；不同 revision 的 namespace 不同。
2. 全部测试：当前完整 pytest 集无回归。
3. API correction canary：固定 5 个 correction 请求，每个最多一个正常 API 调用，不做语义 repair；度量 HTTP、单 JSON、strict schema、新 ID namespace、append-only compile。
4. 进入下一轮真实 10 题之前，API canary 阈值必须为 5/5 schema、5/5 namespace、5/5 compile；否则撤回该方案并保留失败记录。

## 固定评价口径

- 成功只按结构化 schema、原始 JSON leaf、`ContractGraphPatch.create` 与现有 append-only 验证计算。
- 不在运行后调整阈值、用例或指标。
- API 延迟与 token 仅作描述性统计。
