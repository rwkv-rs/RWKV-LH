# Round40 Basic30 逐 Criterion Goal 裁决因果分析

## 固定指标

| 指标 | Round39 | Round40 | 变化 |
|---|---:|---:|---:|
| Strict | 14 | 14 | 0 |
| External | 22 | 26 | +4 |
| Agent completed | 20 | 15 | -5 |
| FP | 6 | 1 | -5 |
| FN | 8 | 12 | +4 |
| 模型请求 | 406 | 486 | +80 |
| Task | 127 | 127 | 0 |
| Attempt | 137 | 135 | -2 |

Strict不降且 FP 从6降到1，满足Round40预注册保留判据；但FN和请求显著增加，不满足上传条件。

- Strict PASS：B01、B02、B07、B09、B10、B14、B15、B16、B17、B19、B20、B24、B27、B30。
- FP：B29。
- FN：B03、B05、B06、B08、B11、B12、B13、B18、B21、B25、B26、B28。
- Agent与External均失败：B04、B22、B23。

## 确认收益

逐criterion接口消除了“多条局部reason否定、一个顶层decision=pass”的表示矛盾。Round39中B30没有生产动作且reason明确说`NotImplementedError`，仍被批量pass；Round40中B30实际完成实现并运行测试后才通过。B04、B22不再误报完成，B20、B27也在本轮产生正确结果后通过。

Controller只按Immutable Goal已有顺序逐项调用RWKV；每项的decision和refs仍由RWKV给出。任一replan或协议/引用失败均不部分提交，测试确认`criterion_claims`和`criterion_evidence`保持空。没有读取reason语义或外部答案。

## FN首因分组

### Goal候选角色错误：8题

B05、B06、B08、B11、B12、B13、B18、B28都完成了正确workspace，但RWKV在一个或多个criterion中选择：

- `actual_ref == expected_ref`；或
- 同一workspace path的action summary与post-action snapshot作为actual/expected。

原validator正确拒绝这些绑定。随后旧goal-obligation replan通常输出完整Task状态或额外字段，再次协议失败。

共同根因不在逐项调用，而在source catalog：

1. `independent_expected_sources`机械包含全部actual sources，名称宣称independent，内容却允许模型直接选择同一ref。
2. 同一写Attempt同时暴露低信息`file written/JSON written`和完整post-action snapshot，弱模型把二者当成两个独立来源，实际共享同一路径与同一产物。
3. catalog没有给出每个actual可合法配对的expected handles，模型必须自己在大量候选中重建独立性规则。

这是接口/状态投影缺陷，不是格式转换问题。

### 不可执行验证Task：4题

- B03：T5要求“所有无关字段与原始内容相同”，单action无法代表跨版本比较；失败后replan schema为`1.0`。
- B21、B25：正确JSON已写入，冗余verify Task的read_json被认为“读取不是验证”；恢复又混入`start_char`并被Harness拒绝。
- B26：recursive listing明确有三个`type=file`和一个目录，Task verifier把四个entries误判为四个文件并重复到budget耗尽。

这些题未到Goal frontier，Round41的catalog整改不应宣称修复它们。

## 唯一剩余FP：B29

B29仍只把源文件最后一行写入backup/source.txt。逐项接口降低了批量矛盾，但RWKV仍把错误producer snapshot绑定到GOAL并判断pass。当前catalog同时保留弱summary、自产snapshot和原始source观察，却没有明确区分“原始输入期望”和“生产后实际”。因此单纯增加调用次数不能消除语义自证。

## 结论

保留criterion-local原子聚合；下一步必须先把source catalog变成真实角色目录：actual使用每个Attempt的最强canonical观察，expected只包含Immutable Goal和未被生产动作污染的原始只读观察，并为每个actual列出机械可配对expected refs。格式层仍只做wire形式归一化。
