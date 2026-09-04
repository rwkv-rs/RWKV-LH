# Round160：gpt-5.6-terra / gpt-5.6-sol FP Trap Canary

日期：2026-08-23

## 目的与固定用例

Round159 只证明中转传输和 strict JSON Schema 兼容性。本轮用 Round158 中 GPT-5.4
错误放行的两个固定用例，检查候选模型作为同一 Contract Graph Planner/Reviewer 时的真实质量：

- E2E-M04：跨三个源组合 JSON 与 Markdown，标题必须同时含 name/version。
- E2E-M08：服务 bullet 必须按 service name 排序且值精确。

分别使用 `gpt-5.6-terra`、`gpt-5.6-sol`；每个模型固定 2 例，总共 4 case。

## 固定配置与门

- 架构、RWKV、reasoning、tokens、graph/review/atom budgets、tool disclosure 与 Round158 相同。
- 每个模型一个独立输出目录，case concurrency=2、atom concurrency=4、GPT 全局串行。
- 每模型 strict=2/2、FP=0、contract_plan_unavailable=0 才通过质量门。
- 固定报告 logical/physical/returned calls、tokens、actions、rejections、raw Final 一致性。
- 只选择进入更大 canary 的候选，不直接更改 `.env`，不替换 R126 或 Round158 配置。

## 数据记录

- 数据仍来自 `data/datasets/rwkv_e2e_90_v1/`；runner 自动记录来源、代码摘要、参数、
  逐例 audit、`RUN_PROTOCOL.json` 与 `source_tree_manifest.json`。
- 输出：
  - `data/experiments/Round160_terra_fp_trap_M04_M08_20260823/`
  - `data/experiments/Round160_sol_fp_trap_M04_M08_20260823/`

