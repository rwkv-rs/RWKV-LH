# Round133 — GPT-5.4 Supervisor + RWKV Worker Full90 预注册

日期：2026-08-21

## 目标

在当前 `chase/hybrid-product-v1` 工作树上测量 `strong-supervisor-rwkv-worker.v1` 的完整
RWKV-E2E-90 产品表现。强模型只生成一次有界计划并审查 RWKV Final；唯一工具选择、参数生成、
workspace 修改和最终答案仍来自固定 G1i-13.3B RWKV Worker。

本轮同时包含当前 progressive tool disclosure 与 Hybrid Supervisor，因此属于当前产品组合测量，
不能把相对 R126/R132 的全部变化单独归因于 Planner。

## 固定配置

- Suite：冻结 RWKV-E2E-90，basic/medium/hard 各 30。
- RWKV：`rwkv7-g1i-13.3b-20260805-ctx16384`。
- RWKV endpoint：本地 SSH forward `http://127.0.0.1:29610/v1`。
- RWKV transport：prompt replay；max transitions 200；concurrency 1。
- Tool disclosure：当前配置 `progressive`。
- Supervisor provider：OpenAI-compatible；model `gpt-5.4`。
- Supervisor temperature：0.1；plan max 1800；review max 1400。
- Final 返修：最多 1 次；Supervisor 无工具执行权且不能改写 RWKV Final。
- 隐藏 acceptance、Codex reference 和 verifier contract 对两个模型均不可见。
- 功能 canary：先运行 E2E-B01；只有 API、因果链、输出非干预和 Strict 全通过才启动 Full90。

## 固定命令

```bash
/home/chase/GitHub/RWKV-LH/.venv/bin/python \
  /home/chase/GitHub/RWKV-LH/scripts/run_rwkv_e2e_benchmark.py \
  --supervisor openai --suite all --case E2E-B01 \
  --max-transitions 200 --concurrency 1 \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/Round133_hybrid_gpt54_canary_B01_20260821

/home/chase/GitHub/RWKV-LH/.venv/bin/python \
  /home/chase/GitHub/RWKV-LH/scripts/run_rwkv_e2e_benchmark.py \
  --supervisor openai --suite all \
  --max-transitions 200 --concurrency 1 \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/Round133_hybrid_gpt54_full90_20260821
```

## Canary gate

1. Supervisor `/models` 含 `gpt-5.4`，plan 和 review 均返回严格 JSON。
2. 恰好提交一个 `supervisor_plan_committed`；Planner 不执行 Harness action。
3. RWKV 原始 Final、解析后的 Final 和交付文本字节一致。
4. acceptance 路径和内容不进入 RWKV/Supervisor trace。
5. E2E-B01 Strict PASS，case audit 与 run protocol 完整。

## Canary 修复登记

- 首次 canary 输出：`Round133_hybrid_gpt54_canary_B01_20260821`。
- 结果：FAIL；Planner 正确，但 supervisor event 中的“direct operations”与 progressive
  `select_tool` 第一阶段冲突，RWKV 的 12 个直接 `list_directory` 调用均被协议拒绝。
- 修复：只统一 supervisor plan/review 的协议提示，明确服从当前显示的 `select_tool -> disclosed
  direct operation` 两阶段；不修改任务、Harness、验收、采样、阈值或工具参数。
- 回归：Hybrid/Progressive、普通 Progressive 和 Supervisor API 专项 29 tests 通过。
- 修复后 canary 固定输出：`Round133_hybrid_gpt54_canary_B01_r2_20260821`。只有 r2 通过原定 gate
  才可启动 Full90。

## Full90 固定评价

- 主指标：Strict、FP、FN、OTHER，沿用现有固定分类与 isolated verifier。
- Terminal target：Strict > 36、FP <= 24、FN <= 1、90/90 valid、0 running。
- 保真：byte-precision B01/B06/B13/B19/B28 = 5/5。
- 同时报告 Supervisor plan/review 次数、REVISE 次数、token usage、延迟、协议拒绝与 RWKV 请求数。
- 不因中途分数、费用或单题表现修改参数、阈值或评价口径。

## Round133 终止结论

- r2 在修复 supervisor 事件的首轮冲突后，RWKV 完成 `list_directory -> write_file`，外部
  `file_content` 验收 PASS。
- 但写入结果返回后，progressive 再次要求 `select_tool` 时，RWKV 连续 12 次复读上一条 direct
  `list_directory`，最终 `protocol_rejection_budget_exhausted`；reviewer 尚未被调用。
- 因 canary gate 第 3/5 项失败，Round133 Full90 按预注册跳过。不得把切换 full disclosure 后的
  结果计入 Round133。
