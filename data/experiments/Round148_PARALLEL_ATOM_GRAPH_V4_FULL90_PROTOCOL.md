# Round148：Parallel Atom Graph v4 Full90 预注册协议

日期：2026-08-22

晋级来源：Round147 exact-dependency-observation canary 的结果与全部架构门均 PASS。运行开始后
不得修改代码、任务、hidden verifier、参数、评分算法或阈值来改善本轮结果。

## 固定配置

- Suite：固定 RWKV-E2E-90（B30 / M30 / H18 / LH12），不生成训练数据。
- 架构：`strong-supervisor-parallel-rwkv-atoms.v4`。
- GPT-5.4：仅在线 Planner/Reviewer；无 Harness action authority，不改写 RWKV Final。
- RWKV：唯一工具执行与 Final 主体；single-operation atoms；mutation budget=1；read budget=1–4。
- 每个 atom 使用隔离 workspace snapshot；仅 completed mutation atom 的声明 write roots 可提交。
- 依赖只传递 bounded exact action observations/artifact metadata，不传 natural-language summary。
- `max_parallel_stages=8`、`max_parallel_atoms=4`、`atom_max_transitions=40`。
- full tool disclosure 进入 Planner operation catalog；RWKV 每个 atom 只看到被选中的一个 operation。
- 每题 `max_transitions=200`；case concurrency=6，理论最大 24 个并发 RWKV atom lane。
- Worker sampling 与 R126/Round138 相同：temperature 0.05、top_p 1.0、top_k 0。
- 输出目录：`data/experiments/Round148_parallel_atom_graph_v4_full90_20260822/`。

## 主要晋级门

1. 90/90 均产生结果、0 running、0 case infrastructure/verifier failure。
2. Strict TP `>36`（超过 R126 official），FP `<=24`，FN `<=1`。
3. 固定 byte-precision 用例 B01/B06/B13/B19/B28 为 `5/5`。
4. R126 official TP retention `>=34/36`。
5. native level 不塌缩并达到 R126 分层下限：B `>=23`、M `>=10`、H `>=2`、LH `>=1` strict TP。

## 架构完整性门

- GPT tool execution count=0；所有 delivered completed Final 与 raw RWKV final byte-exact。
- 所有 mutation atom 均恰好一个 action，且 operation 与声明 operation contract 相同。
- 无 ScopeViolation、InputBudgetError；failed/interrupted atom 的 snapshot 不得提交父 workspace。
- 所有 supervisor stage 数不超过 8；报告 stage/atom 状态、semantic repairs、transport failures。
- 报告至少两 atom 时间区间重叠的 case 数、峰值 lanes、RWKV/GPT 请求数与 token、actions、目录大小。

任一主要晋级门不满足，则不能替换 R126 canonical baseline；无论结果如何，都保留为架构与后续
state-tuning 数据筛选证据，但失败/错误 acceptance 轨迹不得直接作为正样本。

