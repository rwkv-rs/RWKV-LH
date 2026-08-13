# Round40 预注册协议：逐 Criterion Goal 裁决与原子聚合

## 触发证据

Round39 Basic30 的 Goal frontier 同时出现两类结构失败：

1. B30 的四条 binding reason 全部明确说明未实现/不能通过，但一个批量响应的顶层仍是 `decision=pass`；局部判断与全局 verdict 脱节，形成 FP。
2. B12、B18、B21 的 workspace 和 Task 均正确，但一个多 criterion binding 中的重复 ref、同 path lineage 或漏项使整次提交失败；随后进入更复杂的 goal-obligation replan 并因旧外壳阻塞，形成 FN。

弱模型在一个响应里同时完成“逐项判断、逐项选 ref、覆盖集合、再给全局 verdict”负担过高。

## 唯一架构变更

把 Goal frontier 的一个多 criterion 请求拆成固定的 criterion-local 请求：

- Controller只按 Immutable Goal 中已有 criterion 顺序逐项调用同一个 RWKV；不判断 criterion语义。
- 每个请求只展示一个固定 criterion 和完整、未筛选的 causal source catalog。
- 返回对象必须恰好为 `decision` 和 `binding`。
- `decision=pass` 时，`binding` 必须恰好绑定当前 criterion 的 `criterion_id/actual_ref/expected_ref`，可选非空 `reason`。
- `decision=replan` 时，`binding=null`。
- 任何一项 replan、协议失败或 provenance validator失败，整批不提交任何 CriterionEvidence；只有全部 criterion 都 pass且全部引用通过原 validator后才原子提交。

旧的 actual/expected独立性、completed Task owner、succeeded Attempt、workspace path lineage等验证保持不变。source catalog内容和排序保持不变，本轮不做强/弱证据筛选。

## 明确禁止

- Controller不读取 reason 的语义，不把否定词转换为 replan。
- 不根据外部验收、隐藏答案、criterion关键词或文件内容决定 pass/fail。
- 不预选 actual_ref/expected_ref，不自动修复、补齐或改写 RWKV binding。
- 不部分提交已 pass 的 criterion，不通过部分完成绕过失败项。
- 不修改 Task规划、action选择、格式别名、Harness执行结果或最终答案。
- 格式转换层仍只做 wire format归一化，不参与本轮 Goal判断。

## 固定验证

1. 单 criterion pass：仅该 criterion可出现在 binding，引用仍由原 provenance validator验证。
2. 单 criterion replan：binding必须为 null，Controller提交 0 条 evidence。
3. 多 criterion 中任一 replan：此前/此后 pass均不产生部分提交。
4. criterion id错配、额外字段、binding数组、漏字段、同 ref、同 path lineage：fail-closed。
5. 全部 pass：先验证全部 proposal，再一次性写入 evidence。
6. 全量 pytest、LH-Control 30/30、E2E-90 validate-only 90/90。
7. 定向 canary固定为 B04、B08、B12、B18、B21、B22、B27、B29、B30：覆盖已知 FP、正确结果的 Goal绑定失败和已通过 hash案例。
8. canary后运行显式 B01–B30，并与 Round39、Round36固定指标比较。

## 成功判据

- 不再出现一个响应中 reason逐项否定但全局 decision=pass的结构矛盾。
- Goal binding协议错误被限制在一个 criterion，不触发更复杂的批量覆盖错误。
- evidence仍全部由 RWKV引用真实 source ref；Controller semantic fields generated=false。
- Basic30 Strict高于14，或 Strict不降且 FP低于Round39的6；若两者均未满足，则本轮不上传。
