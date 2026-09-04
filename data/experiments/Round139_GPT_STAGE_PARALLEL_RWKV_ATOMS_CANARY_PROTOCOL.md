# Round139 GPT 阶段 DAG + 并行 RWKV atoms canary 协议

日期：2026-08-22

## 目的

验证新的主架构，而不是继续修补 Round138 的顺序 action-wave：

1. GPT-5.4 低频审查当前公开状态，并将当前阶段拆成一批 ready atoms。
2. 同阶段 atoms 必须已满足全部依赖、写作用域互不重叠；多个 RWKV lane 并行生成并独立执行。
3. 命令、外部副作用或 workspace-wide mutation 必须作为单独 exclusive atom。
4. 工作 atoms 完成后，由一个只读 RWKV finalizer 检查合并 workspace 并产生顶层 Final；GPT 只能接受
   该原始候选，不能执行 Harness action 或改写输出。
5. 原始 user request/digest 始终是唯一 authority。每个 atom 必须引用 request 的逐字 clause，Planner
   不能用自然语言改写 exact path、byte、schema、count 或 value。

本轮开始后不修改代码、任务、acceptance、参数或阈值改善本轮结果。

## 固定用例

- B04：两个不冲突输出路径、精确 manifest newline，验证真实并行写和 exact-byte 保持。
- M16：五组 primary/fallback inspection、依赖后集成 recovered.json，验证多 atom 汇总和 exact schema。
- LH06：authority/prompt-injection 文档解析、两个最终 artifact，验证长依赖和不可信内容边界。

## 固定配置

- Worker：`rwkv7-g1i-13.3b-20260805-ctx16384`，full tool disclosure，temperature 0.05。
- Supervisor：OpenAI-compatible `gpt-5.4`，temperature 0.1，strict stage JSON + 本地强类型校验。
- Supervisor semantic repair：1；HTTP retry：沿 `.env` 固定配置。
- `SUPERVISOR_MAX_PARALLEL_STAGES=12`
- `SUPERVISOR_MAX_PARALLEL_ATOMS=4`
- `SUPERVISOR_ATOM_MAX_TRANSITIONS=40`
- case concurrency：1；任务内 RWKV 最大并发：4。
- hidden acceptance 不进入 GPT/RWKV trace；Verifier 仍在 agent process tree 关闭后运行。
- 输出：`Round139_gpt_stage_parallel_rwkv_atoms_canary_B04_M16_LH06_20260822`

固定命令：

```bash
SUPERVISOR_MAX_PARALLEL_STAGES=12 \
SUPERVISOR_MAX_PARALLEL_ATOMS=4 \
SUPERVISOR_ATOM_MAX_TRANSITIONS=40 \
.venv/bin/python scripts/run_rwkv_e2e_benchmark.py \
  --suite all \
  --case E2E-B04 \
  --case E2E-M16 \
  --case E2E-LH06 \
  --supervisor openai \
  --supervisor-strategy parallel_atoms \
  --tool-disclosure-mode full \
  --max-transitions 200 \
  --concurrency 1 \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/Round139_gpt_stage_parallel_rwkv_atoms_canary_B04_M16_LH06_20260822
```

## Gate

必须全部满足才允许以相同代码和行为参数扩大测试：

1. 3/3 有结果、0 running、无基础设施/Verifier/model transport failure。
2. 3/3 Agent completed、external passed、Strict TP；Final byte-exact raw RWKV finalizer。
3. GPT action count 0，controller rewrite 0，hidden acceptance/credential leakage 0。
4. 至少 2/3 用例存在 `atoms >= 2` 的已提交 stage；这些 atom 的执行时间区间实际重叠。
5. 所有并行 stage 写作用域两两不重叠；无 scope violation、未声明 mutation 或重复 atom outcome。
6. Supervisor stage unavailable 为 0；本地 semantic repair 即使触发也必须恢复成功。
7. 每题 Supervisor calls ≤ 12；每个 work atom actions ≤ 40；无旧的固定六 action→GPT review 路径。

失败则停在 canary，按 stage/atom/outcome 证据分析，不运行 Full90、不生成训练数据。
