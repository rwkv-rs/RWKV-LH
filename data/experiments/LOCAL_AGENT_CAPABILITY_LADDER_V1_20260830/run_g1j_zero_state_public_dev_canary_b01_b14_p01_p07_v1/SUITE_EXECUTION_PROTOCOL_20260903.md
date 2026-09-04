# 全 zero State Agent 基线套件执行协议

登记日期：2026-09-03（Asia/Shanghai）  
基准代码起点：`9ae5eda1b8c5196ef401b62414e7d9ffd9243120` 加 `NEXT_STATE_REMEDIATION_RERUN_PREREGISTRATION_20260903.md` 中登记的未提交整改文件哈希。

## 固定顺序与目录

1. 先完成公开 Dev `B01`–`B14`。
2. 每题运行三个固定 run label：`20260902`、`20260903`、`20260904`；label 只区分独立重复运行，不发送为模型 seed。
3. 固定母路径：本目录。
4. 每次运行使用 `public_dev/seed_<label>/cases/PUBLIC-CANARY-<case>-S<label>/workspace`，task 输入不包含绝对路径，也不强调工作区路径。
5. 之后完成 Strong Planner `P01`–`P07`；每题使用本目录下固定、彼此隔离的新空工程目录。

## 固定运行身份

- Executor/Step Auditor/Finalizer/Final Auditor：`rwkv7-g1j-13.3b-zero-state-capability-ctx16384`，模型 SHA-256 `559371f5b9aef13189ae54b345ac096af4ad2b689996c05d89de687612b3ae65`。
- Executor 引擎固定为工程内 `data/runtime/engines/vllm-rwkv-67f0c5996c50`；运行制品固定为 `data/models/rwkv7-g1j-13.3b-vllm-v1`，manifest SHA-256 `4eff9f7054e52d702c43132855e943a8fce3269e578a0160752363775b3d6647`。
- Selector：`rwkv7-g1j-2.9b-vllm-v1`，模型 SHA-256 `c1a316e75abd50f5edc3358fbb2c7d1cb18c611d9b2aa5b888091c8d45cc866c`，Head SHA-256 `71d69959c758fae3bcec8f35f682eb7c9e21f0cf826ffe5cb797d923964473de`。
- 五个生成角色的 State profile SHA-256 全为 64 个 `0`。
- Strong Planner：`gpt-5.6-sol`；Stage Checker：`claude-opus-4-6`。
- Strong 请求：`json_object`；不发送 temperature、seed 或 reasoning。
- Planner cache 关闭、fallback 关闭、semantic repair 为 0、transport retry 为 1。
- G1J 唯一输入格式为 `PromptV1` + `**Tool Call:**` + ` ```json`。
- 单次 Goal 最大 transitions 为 240；只有合法 `final_answer` 经 Final Auditor 接受才终止。

## 固定评分

- B 组以用户冻结规范中的确定性文件/命令 verifier、运行 ledger 与 final evidence 共同评分。
- B11 必须在首次已应用副作用后注入崩溃，并以同一 run store 恢复；B12 必须保持非完成且不伪造报告。
- P 组不以 Agent 自写测试作为唯一依据；使用独立黑盒测试、文件摘要、强制中断/幂等检查与最终事实审计。
- 主要指标为 `full_task_success`；保留用户冻结的全部诊断指标和硬门禁。
- 运行后不修改阈值、验收逻辑、工具菜单或推理参数来改善结果。
- 任何上游模型/服务不可用单独归类为 infrastructure-invalid，不进入能力分母；协议拒绝、错误工具选择、错误参数、未完成与 budget 耗尽均属于有效能力结果。

首次 B01、B02 和未完成 B04（run label `20260903`）因实际使用工程外旧 Executor 引擎而在 2026-09-03 被追溯判为 engineering-invalid 并无损归档。重新运行不改变任务输入、验收、工具菜单或推理参数，只纠正运行时来源，使其符合本协议原本要求的工程固定身份。
