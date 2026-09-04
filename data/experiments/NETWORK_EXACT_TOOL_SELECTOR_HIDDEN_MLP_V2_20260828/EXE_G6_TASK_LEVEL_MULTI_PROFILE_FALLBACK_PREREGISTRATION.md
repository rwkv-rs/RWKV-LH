# EXE-G6 task-level 双 state 备用部署预登记

登记时间：2026-08-30；登记时 G9 固定八检查点消融只完成 step250–1250，step1500
仍在运行，尚未生成 G9 `ABLATION_RESULT.json`，也未运行本文件定义的任何 multi-profile、
Full90、live 或 Agent V1 推理。

## 触发条件与问题边界

本实验仅在 G9 完整消融结果为 `no_candidate_passed` 时触发。它不修改 G9 已登记的
G4/G6/holdout/retention 门槛，也不把 G6 step1500 的 310/336 general retention 重新解释为
通用能力通过。G6 仍不得作为 universal state。

要回答的问题是用户在实验前提出的另一种架构假设：state 可以分开存储，并由同一个 13.3B
Executor 在不同**任务**中显式加载；联网任务和纯本地任务的 state tuning 目标不同，最少两个
task-level state 可能优于一个强行合并的 state。

冻结输入：

- G3 消融结果 SHA-256
  `0f2d4c9c286ba9c1c03fd0678aad1faa9edc62d2c0e2f2cd65d5e3993ed2d2e5`；
- G6 消融结果 SHA-256
  `8ca74af573a0aaae7503e585d4196d70622e8b7bffaa538d5e986c1ad2c0df2e`；
- G3 profile：`EXE-G3-MULTISTAGE-STEP2000`，state SHA-256
  `13f6586951666962405286dda8e45c1eae82a37c68c21b3b75dbbb04c6e54f12`；
- G6 network profile：`EXE-G6-NETWORK-RECOVERY-STEP1500`，vLLM state SHA-256
  `611d9e5564ef47413c1bd1536500e987270c8303b2c87d5d54bca256d57dd68b`；
- Agent V1 能力矩阵预登记 SHA-256
  `d54fdfd9abe0282259222df732980dd9fb60fb22670e4bb98133b57706d9cdb2`；
- G9 Stage C 引擎预登记 SHA-256
  `5e5105dbfac93ec6277d3d881b19421215385cac7859137747d4969716f9d9b8`。

## 冻结部署臂

1. `A_GENERAL_G3`：所有纯本地/`retrieval.mode=offline` 任务在 task 创建时固定 G3；
2. `D_DUAL_G3_G6`：`retrieval.mode=offline` 固定 G3，其余显式联网模式固定 G6。

绑定只能读取 task 创建时的 immutable policy field，不读取自然语言关键词、selected operation、
执行阶段、动作结果或模型输出。一个 task 内 main lane 与 atom worker 必须使用相同 profile；
Selector 固定为 2.9B S60 zero-state Hidden(mean+last)+h64 MLP。Planner/Reviewer 不获得工具权限。

G6 的适用范围只由联网任务完整闭环验证：检索、证据绑定、文件写入、命令执行、失败恢复、复读和
RWKV final 都在同一个 G6 task-level state 下完成。不得在检索后切回 G3，避免重复加载造成信息
损失，也不得由 Controller 修补 Executor 参数。

## 固定引擎门槛

沿用已冻结的隔离 `vllm-rwkv` multi-profile overlay、物理 GPU0、实验端口 18075，并全程保留
产品端口 18070。manifest 默认 native zero，显式登记 G3/G6；每个请求必须同时提交 profile ID
与 SHA-256。

必须满足：

1. 缺 ID/digest、未知 ID、错误 digest、损坏 state、错误 base identity 在分配 recurrent state
   前失败关闭；zero/G3/G6 精确 pair 成功；
2. 冻结 recovery72 按 `G3→G6`、`G6→G3` 两种顺序交替，同一 `(profile,sample)` 的 raw text、
   token IDs、finish reason 与 canonical pass/fail 跨顺序相同，并等于 dedicated-process 证据；
3. 每个 task 的 main/atom Executor profile switch=0，Selector switch=0；
4. multi-profile warm p50 不超过 dedicated 的 1.25 倍，p95 不超过 1.35 倍；
5. prompt、采样、请求顺序、response、append-only raw journal 和评价算法不变，RWKV 原始输出
   modification/deletion/reorder/hide 全为 0。

## 固定质量与能力门槛

- `A_GENERAL_G3` 运行冻结 Full90；`D` 的 90 个 offline task 逐 case 证明生产 routing 解析为同一
  G3 ID/SHA/request delivery，直接复用不可变 A 证据，避免重复随机/provider 调用；
- `D` 使用 G6 完整运行 live V1 2/2、grounded V2 6/6、retrieval hard gates 9/9；
- `D` 必须运行 Agent V1 的 `公开资料查证→本地文件修改→本地测试→复读→RWKV final` 联动例，
  且该 task 从开始到结束只使用 G6；引用只能来自已提交 evidence；
- 再按既有 Agent V1 预登记运行 WEB01 与九个旧能力 case。离线 case 必须请求 G3，不能用 G6
  或按结果挑 profile；WEB01 必须 external pass、completed、公开 verifier exit0；九例 external
  与 completed 均至少 8/9，M02/H07/LH12 必过；
- Planner tool event=0、scope violation=0、acceptance leakage=0、hidden retry=0、postprocess=false；
  完整项目回归与 `git diff --check` 通过。

## 固定结论规则

只有引擎门槛、联网门槛、联网本地联动和 Agent V1 全部门槛同时通过，才可选择
**G3 general + G6 network 两个 task-level Executor state** 作为第一正式简体版。这个结论仅说明
双 state 架构通过，不撤销 G6/G9 universal state 的失败结论。

任一门槛失败均不得激活该配置；失败簇用于下一轮独立 state tuning。不得降低门槛、增加
operation/阶段路由、重复模型调用、注入验收答案，或修改/删除/重排/隐藏 RWKV 原始输出。
