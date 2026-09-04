# Round58 预注册协议：一次 evidence-local reselection

## 假设

Round57 的剩余 FN 来自一次 source selection 不稳定，而不是语义裁决错误。若 semantic adjudication 返回 insufficient，先在同一 criterion 内把该原始理由反馈给 RWKV 并允许一次重新选源，可避免过早进入全局任务重规划。

## 唯一改动

- 每个 criterion 最多两轮 source-selection → isolated-adjudication。
- 第一轮 insufficient 时持久化原始 reason、actual_refs、expected_ref；第二轮 source selector 收到这些原始字段和完整同一 catalog。
- 第二轮必须由 RWKV 返回不同或扩展的 actual_refs/expected_ref，或明确 replan。控制器只做“是否完全相同”的无进展检查，不添加、删除、排序或替换 ref。
- 第二轮 supported 才提交 claim；第二轮 insufficient 或 replan 才进入既有 Goal obligation recovery。
- 其余 Round57 时间化多源、历史 expected、严格 adjudication 隔离和透明格式归一化全部保持不变。

## 不作弊边界

- insufficient reason 原文透传，不由控制器摘要或改写。
- 控制器不得根据 criterion 或 source 内容推荐候选。
- supported/insufficient、第二轮 refs 和最终答案全部保持 RWKV 原始语义字段。

## 验证

- 离线门槛：pytest 全量、LH-Control 30/30、catalog 90/90、31-file 全通过。
- 固定 15 题与 Round56/57 相同。
- 必须保持 FP `0` 或至少不高于 Round46 同组 `7`，FN `<=1`；B01/B02 不回归；若 B24 外部正确，则必须不再因原集合 M-T1 直接进入 obligation replan。
- 通过 canary 后才允许 E2E-90；上传门槛不变：Strict `>31/90`、FP `<=24`、FN `<=1`。

