# 快速 Agent 能力 Canary V1 预注册

登记时间：2026-08-31（Asia/Shanghai），在本轮任一模型请求前冻结。

## 目的与边界

本轮只回答当前最佳已验证部署能否闭环完成三类代表性真实任务：通用 bug 修复、中型网页项目、
联网证据驱动项目。它不是完整 10 题 Agent Ladder，也不据此推断能力上限或成熟 Agent 百分比。

0.4B State Router Shadow 已退出当前产品链路。本轮只能使用强模型 Planner/Reviewer、2.9B
S60 Hidden+MLP Selector、13.3B G3/G6 Executor 和真实 Harness；Shadow 不启动、不调用、
不进入指标。

## 冻结数据与顺序

- suite：`agentladderv1`
- tasks SHA-256：`23cf009831fb38dd05bd3fad69e246a822a59ab6bd725833c6df2aaaf45c93bb`
- hidden acceptance SHA-256：`f95da0b4085cdee3bc4555255dfb4f09d9272c00982634c72a040361c5774e06`
- 固定顺序：
  1. `AGENT-LADDER-L1-FIX01`
  2. `AGENT-LADDER-L4-LEDGER01`
  3. `AGENT-LADDER-L5-RWKV01`
- acceptance 不进入 Planner、Selector 或 Executor 输入。
- 不修改任务、验证器、评价算法或阈值；失败后不得覆盖本轮目录。

## 冻结架构与身份

- Planner/Reviewer：`gpt-5.4-mini`，Contract Graph，plan/review token 上限
  `4000/2400`，reasoning effort 均为 `none`，无 fallback；本轮关闭 plan cache，
  每个阶段实际调用 API。
- Selector：`rwkv7-g1i-2.9b-vllm-v1`，GPU0，S60 requirement-byte-tail，
  model SHA-256 `01f39dd59fc402fbe8ba49765a1997ee9dbc82427bf0ece6a4fac520e9eb8044`，
  head SHA-256 `721669ce8733b590b3aa6c910d8bc13d744612f1fee884d5276a3f0d96d0d441`，
  input protocol `rwkv-lh.exact-tool-selector-input.v7-requirement-byte-tail`，zero profile。
- Executor：`rwkv7-g1i-13.3b-exe-g3-g6-deterministic-cmix-r7-multiprofile-ctx2496`，
  base SHA-256 `5d97772ba04a81bdaeba90e1d6d306c70560bf4f784522be61cdcade69e30562`。
- 离线任务绑定 G3 `EXE-G3-MULTISTAGE-STEP2000`，SHA-256
  `13f6586951666962405286dda8e45c1eae82a37c68c21b3b75dbbb04c6e54f12`。
- 联网任务绑定 G6 `EXE-G6-NETWORK-RECOVERY-STEP1500`，SHA-256
  `611d9e5564ef47413c1bd1536500e987270c8303b2c87d5d54bca256d57dd68b`。
- state profile 按 task 的冻结 retrieval policy 只绑定一次，同一 task 内不切换。
- Executor endpoint：`http://127.0.0.1:29613/v1`；Selector endpoint：
  `http://127.0.0.1:29621`。
- Harness tool disclosure：`progressive`；独立 selector：开启；并发：`1`；
  max transitions：`300`。

## 冻结实现

- benchmark runner SHA-256：`128532c06a6995bd7e6cffd71a17dd6cf1e3b9133d05eafa961eb6391fd2b3f2`
- controller SHA-256：`763614d449c2755d5eb3c07b438214b798a082569cdc7c5d5c4eb327092399a4`
- supervisor SHA-256：`ba626e758817e0dbb2c55a6c8deb9eacf97d75448ca627ba15c0c5c83dfbaf77`
- parallel atoms SHA-256：`8eea0be4bcb21498d8de6540e1cf9998ff8bba0f4a623760cd78e1a876a203bb`
- retrieval runtime SHA-256：`39f52c282a1744c81fa62c8a14228022a600449fc658cef804943ed361f5807f`

## 指标与判定

逐题固定报告：`agent_completed`、hidden external acceptance、strict E2E、RWKV 请求数、
Supervisor 请求数、Action 数、协议拒绝和失败类型。

- canary 通过阈值：三题 `agent_completed=3/3`、external=`3/3`、strict=`3/3`。
- 任一题失败均如实保留，禁止通过修改 evaluator、任务或原始输出来改善结果。
- RWKV prompt、raw output、protocol normalization、工具结果与最终输出逐项保存；绝不修改、
  删除、重排、隐藏、截断、修补或替代 RWKV 原始输出。
