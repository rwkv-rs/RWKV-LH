# G1J 13.3B zero-State 单职责输出 canary 结果

- 结果：`0/3`，固定 gate 失败。
- 模型身份：`rwkv7-g1j-13.3b-20260831-ctx16384`。
- State profile：未发送。
- 服务请求：三例均成功完成，不是 HTTP、显存或模型身份失败。

## 最早失败层

三例最早均失败于 `output_protocol`：输出不能被当前严格解析器接纳为一个完整函数调用对象。

1. `V2-CORR-OPARGS-0001` 输出一个 `function_call` 后追加了代码围栏闭合符，导致 strict JSON object parser 拒绝；即使只观察语义，模型选择的是 `current_time`，固定标签为 `write_file`，因此还存在独立的工具意图错误。
2. `V2-CORR-AUDIT-0001` 没有输出六字段 Audit decision，而是把 Audit boundary 重新包装成新的 `event_type=tool_call`，随后自行生成不存在的 `fetch_evidence` 多轮轨迹。
3. `V2-CORR-AUDIT-0002` 没有输出 Audit decision，而是重复续写已有 `action_result`，直到达到 256 token 上限。

下游没有机会执行，因此不是下游继承错误；三例都在首个 13.3B generation 内产生独立错误。完整 raw generation、usage 和 parser error 保存在 `RESULT.json`。

复核发现该独立 canary 没有发送产品 `ModelSession` 使用的 stop suffix。因此第一例尾部代码围栏和 Audit 后续多轮续写的长度不能当作产品 parser 缺陷；这是 canary transport 与产品不一致。该差异不改变首个对象的语义证据：第一例首对象仍误选 `current_time`，两例 Audit 的首对象仍不是六字段 `audit_decision`。后续产品一致性诊断必须补齐 stop suffix，并使用最新 role-pure Auditor 模板。

## 归因边界

这些固定输入属于旧 correction prompt，结果证明的是“旧输入模板在 G1J 13.3B 上不可靠”。它不能直接证明最新 role-pure Auditor 模板仍失败，也不足以启动 State Tuning。下一步先用当前模板做诊断复核；只有在当前职责边界和 prompt 尾部布局正确后仍可重复失败，才把对应失败改正并进入候选 tuning 数据。
