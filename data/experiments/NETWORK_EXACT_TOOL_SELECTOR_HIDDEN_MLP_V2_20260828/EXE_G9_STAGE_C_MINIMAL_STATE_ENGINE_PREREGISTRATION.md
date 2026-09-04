# EXE-G9 Stage C：最小 Executor state 与本地引擎联动预登记

登记时间：2026-08-30；G9 正在 GPU0 训练，尚未运行任何 G9 checkpoint 推理、
live Stage B 或多 profile 引擎推理。

## 目标与边界

本实验只回答一个部署问题：在 2.9B S60 Selector 与 13.3B Executor 已分离的当前
架构中，第一正式版本最少需要几个 Executor initial-state profile。state 不跨模型导入，
也不在一个 run 的阶段间切换。Planner 只编译/审核 Contract Graph；Selector 只选择
operation；Executor 生成参数、推进工具、恢复拒绝并给出原始 final。

只有 G9 离线消融与 Stage B 全部门槛通过，才允许执行本实验。实验不会通过 Controller、
Parser、Harness、Resolver 或重复模型调用修补 G9 输出。每个 response body、text、token IDs、
finish reason、model/profile identity 都先 append-only 保存。

## 固定三种部署臂

1. `A_GENERAL_G3`：所有离线任务固定 `EXE-G3-MULTISTAGE-STEP2000`；作为当前架构
   同代码、同 S60、同采样的 general 对照。
2. `B_UNIVERSAL_G9`：离线与联网任务都在 task 创建时固定离线消融选出的 G9；
   每个 lane 只加载一次。这是 state 数最少的优先候选。
3. `C_DUAL_G3_G9`：immutable `retrieval.mode=offline` 固定 G3；其余模式固定 G9。
   选择只读取策略字段，不读取请求关键词、operation、阶段或模型输出。

三臂的 2.9B Selector 始终是 S60 zero-state Hidden(mean+last)+h64 MLP，不随 Executor
profile 改变。`B` 与 `C` 的联网任务应产生相同 Executor profile identity；`A` 不用于
替代 G9 的联网质量结论。

## 固定引擎与隔离门槛

使用 pinned local `vllm-rwkv` revision
`67f0c5996c50dca0ad779da545cb491527de988f` 的隔离副本，远端仅监听 18075，物理
GPU0；现有产品 18070 全程保留。manifest 默认必须是 native zero，显式预加载 zero、G3、
胜出 G9 三个 identity；请求必须同时提供已登记 profile ID 与 SHA-256。

必须通过：

1. 缺 ID、缺 digest、未知 ID、错误 digest、损坏 state、错误 base identity 均在分配
   recurrent state 前失败关闭；zero/G3/G9 精确 pair 成功。
2. 冻结 G6 recovery72 以并发 1 按 `G3→G9` 和 `G9→G3` 两种顺序完整交替；同一
   `(profile,sample)` 的 raw text、token IDs、canonical pass/fail 必须跨顺序完全一致，
   且等于各自 dedicated-process 证据。
3. 每个 task 的 Executor lane profile switch=0；同一 task 的 main 与 atom worker profile
   identity 完全一致；Selector lane 也为 0 switch。
4. multi-profile 的 warm p50 不超过对应 dedicated process 的 1.25 倍，p95 不超过
   1.35 倍；startup 不计入 warm latency，但不得删掉原始延迟记录。
5. 任一 profile 请求不得改变采样参数、prompt、response 或 raw journal 规则。

## 固定质量消融与最少 state 选择

- `A_GENERAL_G3` 与 `B_UNIVERSAL_G9` 各运行冻结 Full90，使用相同源码、case 顺序、
  S60、temperature0.1/top-p1/top-k0/seed1067、max transitions 与强 Planner 配置。
- `C_DUAL_G3_G9` 的离线 Full90 必须逐 case 复现 `A` 的 strict-pass、external-pass、
  completion、首次偏离类别和 profile identity；不得借双 state 改变离线结果。
- `B` 与 `C` 各运行冻结 live V1 2/2、grounded V2 6/6、retrieval hard gates 9/9；
  两者联网逐 case 结果与 raw Executor 输出必须一致。

选择规则固定如下：

1. 若 `B` 的 Full90 strict/external/completion 都不低于 `A`，所有 `A` strict-pass case
   在 `B` 中零回归，且全部引擎/live 门槛通过，选择 **一个 universal G9 Executor state**。
2. 否则，只有 `C` 精确保留 `A` 的离线结果且通过全部引擎/live 门槛时，才选择
   **G3 general + G9 network 两个 task-level state**。
3. 其他情况不激活 G9；不得降低门槛、增加 operation/阶段路由或按结果挑 profile。

最终报告同时登记 state 数、每个 state 的职责、base/state/manifest/engine SHA、GPU、
完整 raw journal、逐 case 指标和延迟。没有此证据不得把 `.env.local` 的 profile routing
改为正式启用。

