# RWKV-LH Stage7 Factory seed v1

本目录是 Stage7 的公开语义种子，不含 operation label、Controller 状态、评测答案或私有 oracle。
`seed_plan.jsonl` 交给 `/home/chase/GitHub/RWKV-state-factory` 扩展 surface family；最终标签只在
RWKV-LH 中经 ActionHarness/Controller 回放产生。

用途、配额、训练和验收均冻结在
`data/experiments/RWKV_STATE_TUNING_STAGE7_FACTORY_CONTRAST_V1_20260827/PREREGISTRATION.md`。
