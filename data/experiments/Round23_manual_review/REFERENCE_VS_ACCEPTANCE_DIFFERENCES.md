# Round23 Codex独立参考答案与acceptance差异

## 边界

独立参考答案已先以 SHA256
`d27befd580de64b370d6c00d94b10529f96aca3d9b015eae8bb7eadae44d9aa2`冻结。本文件之后才读取三套
acceptance。这里区分：

- **独立答案错误**：题面已足以判定，Codex理解错误。
- **独立答案过度解释**：题面有歧义，但acceptance选择更自然，后续分析采用acceptance并保留原答案错误记录。
- **acceptance收窄**：题面未指定某个key、空行或禁止额外字段，acceptance却使用exact equality/content固定了实现形状。
- **一致**：其余题的可观察值、计算关系和代码行为均与acceptance一致；代码/文档的非唯一bytes按运行时digest检查。

## 有差异的题

| case | 类型 | Codex独立答案 | acceptance | 后验结论 |
|---|---|---|---|---|
| B27 | 独立答案错误 | 认为`fallback_protocol=v1`应保留 | 要求所有`protocol=v1` substring消失，包括fallback行 | “no v1 occurrence remains”消除了歧义；后续以acceptance为准。Round23实际仍留两处v1，因此不影响其失败结论，但盲审中“fallback应保留”需在后验记录中纠正。 |
| M14 | acceptance收窄 | date后直接开始bullets | date后固定一个空行 | 用户只要求title、date line和bullets，没有规定空行；按Strict仍以acceptance exact bytes评分。Round23 Markdown内容本身也完全错误，不只是空行。 |
| M25 | acceptance收窄 | 两个version group连续 | group之间固定一个空行 | 用户没有规定group间空行；Round23还使用`write_json`写成quoted string且1.2内部顺序错误，故不是仅口径问题。 |
| M29 | acceptance收窄/答案过度解释 | 翻译key平铺在顶层 | 放在`translations`对象内，顶层另有locale/missing_keys | 题面没有明确`translations` key。Round23仅输出locale已有的hello/save，连base缺失回退也没完成，所以无论两种schema都错误。 |
| H08 | 独立答案过度解释 | 每个event entry带frequency count | `{event_ids:[first-seen unique ids],count:3}` | “unique event ids … and a count field”更自然地指unique列表与总count。Round23的map既不保持first-seen数组，也未真实完成resume。 |
| H17 | 独立答案过度解释 | 每个id聚合frequency/total | 保留每个unique id的首个`{id,amount}`，顶层count=3,total_amount=13 | 题面语法可歧义；acceptance将count/total放在ledger顶层。Round23实际数组缺外层且用聚合字段，严格失败；resume-after-completion也未发生。 |
| LH04 | 独立答案过度解释 | 每个id聚合frequency/total | unique首个event数组，顶层count=3,total_amount=13 | 与H17同类。Round23数组还增加first_seen_index、缺顶层count/total，post-effect crash完成态未成立。 |
| LH06 | acceptance收窄 | key为`authoritative_source` | key固定为`source` | 用户只说“containing the authoritative source path”，未命名key。Round23选择和值语义正确但Strict JSON失败；EVIDENCE还是JSON字符串且authority数值错误，不能据此视作整题语义正确。 |
| LH07 | acceptance收窄 | 只固定“report列出排序名称”，未指定key | key固定为`migrated` | Round23用`services`；即使改key，8个service仍有11项迁移违规，故key不是主因。 |
| LH09 | acceptance收窄 | api_result保留finalize response的status/operation | exact JSON只允许resource/finalized | 用户没有说“exactly”或禁止额外response metadata。Round23仍缺duplicate replay（conflicts=0），所以主流程确实不完整；额外字段只是一项Strict差异。 |
| LH11 | acceptance收窄 | 将准确path理解为entry字段`path` | 字段名固定为`artifact` | 用户只要求包含exact artifact path，未命名key。Round23 0 action，无任何checkpoint/summary，故此差异未参与本轮实际失败。 |

## 结论

- 90题中有11题存在某种表达差异；其中B27是明确的独立答案错误，H08/H17/LH04是独立答案过度解释，其余主要是
  exact acceptance固定了题面未命名的表示。
- 这些差异不能用于放宽本轮预注册Strict指标；Round23仍按冻结acceptance计分。
- 下一轮结构不得读取acceptance后为这些key或空行建立case特判。若要减少评价歧义，应在未来数据集版本中修改公开题面或
  acceptance版本，并重新预注册，而不是让Controller替RWKV改最终payload。
