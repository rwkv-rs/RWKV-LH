# Round8 Copy-Resistant Binding Contract 专项分析

本分析只在 90 题全部结束后读取 hidden acceptance 与冻结的 Codex reference；两者没有进入 validation、
binding、proof 或任何 RWKV 请求。

## 结论

非 JSON 行协议减少了输入 metadata 对输出 schema 的直接污染，但只改善了格式入口，没有改善证据语义：
External `12/90`、Strict `0/90`、Agent completed `0/90`、FP `0*`、FN `12`。Round8 与 Round7 的
External/Strict/Completed 完全持平，模型请求从 1148 增至 1154，不能上传。

## Phase B 漏斗

| 指标 | Round7 | Round8 | 变化 |
| --- | ---: | ---: | ---: |
| Phase B case | 20 | 19 | -1 |
| Phase B event | 41 | 45 | +4 |
| binding response | 79 | 88 | +9 |
| accepted response | 8 | 13 | +5 |
| accepted response rate | 10.13% | 14.77% | +4.65pp |
| protocol-valid event | 8 | 13 | +5 |
| exact proof claim | 8 | 15 | +7 |
| VERIFIED claim | 2 | 0 | -2 |
| CriterionEvidence | 2 | 0 | -2 |

45 个 `assertion_binding_contract_prepared` 事件全部保存了 Phase A intents 和实际行协议；其中 0 个重新包含
四个 input-only metadata key。最常见的“binding fields 必须精确匹配”错误从 53 次降到 29 次，证明边界呈现
确实改变了弱 RWKV 的格式行为。与此同时，argument-field 错误增多，说明模型仍把 operator 名或不适用参数带入
arguments；运行时没有删除、重命名或补齐这些字段。

## Proof 拒绝

13 个合法 event 形成 15 条 assertion，全部 REJECTED：

- 9 条引用的 task/artifact 不是 active task 的 direct dependency；其中 8 条 actual/expected 都选择
  `dependency_artifact_json`。
- 4 条选择不存在的 JSON pointer `/home`。
- 1 条选择不存在的 JSON pointer `/feature`。
- 1 条 `goal_literal.goal_quote` 不是 `Goal.original_request` 的精确非空子串。

因此 Round8 支持“统一、抗复制的模型边界协议可借鉴”，但反驳“只要格式合法就能形成可靠证据”。下一步若继续
证据路径，应复用已经对 RWKV 更稳定的单工具 G1i 调用，让每个 claim 单独填 binding；parser 仍必须 fail-closed，
proof ownership、direct dependency 和独立来源边界不变。

机器明细见 `binding_contract_analysis.json`。
