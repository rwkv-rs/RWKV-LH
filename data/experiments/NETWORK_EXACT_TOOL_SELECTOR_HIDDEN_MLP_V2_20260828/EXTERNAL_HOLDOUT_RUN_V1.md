# Selector v2.4 ECRA 45-case External Holdout Run v1

- 冻结日期：2026-08-28（Asia/Shanghai），holdout feature 提取前登记。
- 数据：`data/datasets/rwkv_lh_ecra_route_v1/cases.json` SHA-256 `7bff832c2668136655272d06ee9545a65094552c7fd4fc14c3d301acae37fa1a`。
- 只取既有 25 个 `public-web-required` 与 20 个 `structured-connector`；不进入训练、early stop、temperature 或 artifact 修改。
- 每例 projection：`task_request=instruction`、`stage_objective=instruction`、`stage_role=work`、零 progress；使用冻结 v2 menu。
- 2.9B batch=1 一次 forward 同时取 last/mean；不生成文本、不采样。
- 两个已冻结 head 直接输出完整 25 raw logits；禁止 mask、规则改写、重试或输出修复。
- 通过门槛继承主预注册：overall accuracy≥0.80，web recall≥0.75，connector recall≥0.75。
- feature 选择顺序固定：synthetic test macro-F1、external holdout accuracy、synthetic test accuracy；全相同选择 last。候选必须同时通过 synthetic 与 external 门槛，否则不得接入。
