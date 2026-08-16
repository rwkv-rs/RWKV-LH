# Round59 预注册协议：reason-first 多源 Goal adjudication

## 假设

Round56-58 的主要 FN 来自 source selection 与 semantic adjudication 分属不同请求。将它们合并为一次 reason-first RWKV 决定，可让模型在同一推理中查看完整真实 source catalog、选择所依赖的 refs 并提交 supported/insufficient，减少跨请求意图漂移。

## 唯一结构改动

- 每个 fixed criterion 只发一个协议类型 `goal_criterion_evidence_adjudication`，最多一次格式纠正。
- 输入仅含 fixed criterion 与 Round57 时间化 source catalog，不拼接其他 memory/context。
- 输出恰好 `reason,decision,binding`，顺序要求 reason 在前；decision=`supported|insufficient`。
- supported 时 binding 恰好为 `criterion_id,actual_refs,expected_ref`；insufficient 时 binding 必须为 null。
- 控制器验证 refs、owner、attempt、digest、时间角色和 live current actual；不得生成/改写 reason、decision 或 refs。
- 移除 Round58 evidence-local reselection；不保留并行的第二套 Goal 语义状态机。

## 与 Round46 旧合并协议的差异

- 必须 reason-first，而非无理由 pass。
- actual 支持显式多 refs 和历史/当前时间语义。
- 模型看到的是完整真实 observation 内容与可审计 digest，不是只有 ref/preview 的宽松 pass。
- supported claim 只绑定模型在同一回答中声明使用的 refs；未选 memory 不进入 claim。

## 不作弊边界

- Controller 不对 criterion/source 做相关性评分、筛选、排序之外的语义处理；新到旧排序是固定事实顺序。
- 不读取 external verifier，不根据 case id 分支，不改变 RWKV 最终答案。
- 透明格式兼容仍只允许删除正确固定 schema 回显、把 singular actual_ref 原样包装为一元素 actual_refs。

## 验证门槛

- 离线：pytest、LH-Control 30/30、catalog 90/90、31-file 全通过。
- 固定 15 题不变；B01/B02 不回归；FP 不高于 Round46 同组 7；FN `<=1`；Strict 至少恢复到 Round46 同组 6/15 才运行 full90。
- 上传仍要求 full90 Strict `>31`、FP `<=24`、FN `<=1`。

