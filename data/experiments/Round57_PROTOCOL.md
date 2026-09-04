# Round57 预注册协议：时间化多源 Goal 证据边界

## 假设

Round56 的主要 FN 不是 semantic adjudication 本身，而是证据接口只能选择一个、按旧到新排列的 observation，并且 adjudication 仍可看到未选 memory。若把来源表达改为时间化多源集合并严格隔离裁决上下文，RWKV 可以在不由规则代判的前提下同时降低 FN 和保持 FP 控制。

## 预注册改动

这是一个完整的 Goal evidence boundary v2 变量组，除此之外不修改 Goal parse、Task decomposition、action harness、Task postcondition、recovery 或 external verifier。

1. `causal_actual_sources` 保留全部合法候选，但按 observation 新到旧展示；每项增加确定性的 task order、recency rank、current workspace match 与 superseded path 元数据。
2. RWKV source selection 输出恰好 `decision,binding`。`binding` 为 `criterion_id,actual_refs,expected_ref`，其中 `actual_refs` 是 RWKV 自选的非空、去重、最小充分集合；控制器不增删、重排或替换。
3. historical original read 可以作为同一路径 current actual 的 expected。独立性按不同 ref/attempt/digest 验证，而不是禁止同一路径的两个时间点。重验 historical expected 时只校验 append-only memory digest；current actual 仍校验 live workspace digest。
4. semantic adjudication 只收到 fixed criterion、全部 selected actual observations、selected expected source；不得拼接未选 memory 或完整 Goal validation capsule。
5. semantic adjudication 输出恰好 `reason,decision`。请求类型固定协议版本，RWKV 不再复述固定 schema。控制器不得补 reason/decision/ref。
6. 透明格式层只兼容两种既有常见拼写：丢弃值正确的固定 `schema_version` 回显，以及把单个 `actual_ref` 原样包成一元素 `actual_refs`。转换前后 payload、摘要和转换名必须持久化；不得生成、删除或替换任何 ref/decision/reason。

## 不作弊边界

- 控制器不得按 criterion 文字打分、筛选、自动选择或改写 actual refs。
- recency/current/superseded 只来自任务顺序、artifact revision 和真实 digest，不包含“相关/正确/满足”等语义标签。
- semantic supported/insufficient 只能来自 RWKV 原始字段；格式层不得改变 verdict。
- 不读取 hidden external checks，不根据 benchmark id 分支，不修改 RWKV 最终答案。

## 固定验证

- 离线：pytest 全量、LH-Control 30/30、catalog 90/90、31-file architecture。
- 固定 canary 与 Round56 相同 15 题：B01、B02、B10、M01、M03、M06、M12、M16、M18、H12、H13、LH02、LH05、LH11、B24。
- Canary gate：Strict 不低于 Round46 同组 6/15；FP 不高于 Round46 同组 7；FN 不高于 1；并且 M03/B24/M12 至少两个不再因选择 M-T1 产生 FN。
- 只有通过 canary 才运行完整 E2E-90。上传门槛仍为 Strict `>31/90`、FP `<=24`、FN `<=1`，且所有离线回归通过。
