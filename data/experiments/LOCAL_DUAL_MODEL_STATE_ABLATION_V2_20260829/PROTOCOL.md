# Local Dual-Model State Ablation V2 — 预注册协议

登记时间：2026-08-29（Asia/Shanghai）

> 数据源修订：第一次写出前预检按固定 `0.95` 相似度门槛拒绝 Round1 五工具补充源；后续
> 使用不改变指标/阈值的 [PREREGISTRATION_AMENDMENT_1.md](PREREGISTRATION_AMENDMENT_1.md)。
>
> 执行身份修订：S31 与正式 S39 Head 的冻结 portable identity 不相容，服务在推理前正确
> fail closed；不得关闭校验拼接。当前可执行矩阵及 request-last 输入冻结见
> [EXECUTION_AMENDMENT_2.md](EXECUTION_AMENDMENT_2.md)。

## 目标与冻结架构

目标是在已经验收的独立 2.9B Selector + 13.3B Executor 架构上，确定满足本地质量和性能的
最少 initial-state profile 数量。不得退回“13.3B 同时选择与执行”，也不得让分类器、Parser、
Harness 或强模型代替 RWKV 生成参数、推进任务或总结。

```text
2.9B Selector: task + stage + compact progress + 25 names/descriptions
    → raw hidden → frozen h64 MLP → committed selection_id

13.3B Executor: task decision-state + exactly one committed tool schema
    → raw complete params / final text → mechanical Harness → exact observation
```

Selector 和 Executor 的 recurrent state、initial profile、checkpoint、输入投影和训练数据完全
分开。一个 lane 从创建到结束维持其 state；除非另开有身份的功能 lane，禁止在同一 lane 的
每个阶段重载 profile。

## 原始输出硬合同

1. 禁止 guided/constrained decoding、grammar、allowed token、logit bias、隐藏 retry、答案
   repair 或任何把 RWKV 输出改成目标调用的逻辑。
2. raw text、raw token IDs、finish reason、response/model/profile identity、采样参数和 UTF-8
   SHA-256 在解析前只追加保存。
3. Parser 只生成派生视图；失败候选不得删除或覆盖。协议拒绝是新的 causal event。
4. Selector 原始产物是完整 25 logits 与身份；不得后处理类别。Executor 不接收 logits。
5. server response → runtime audit → causal event 的 raw SHA 一致率必须 100%。

## Profile 编号与资格

| ID | 资格 | 定义 |
|---|---|---|
| `SEL-Z0-S39` | 正式基线 | accepted S39 h64 Head + zero state |
| `SEL-S31-R` | 诊断、不可晋级 | 2K tuned state；冻结决策净改善 1/500，已拒绝 |
| `EXE-L0-S8R3` | 历史污染对照 | 旧 selector/stop state，线上 step1700 |
| `EXE-Z0-V2` | 正式零基线 | 13.3B base、zero state、新 Executor V2 prompt |
| `EXE-G1-V2` | 首个候选 | 从 base zero 训练的单一通用 Executor state |
| `EXE-F1-V2` | 条件候选 | final-only residual state |
| `EXE-R1-V2` | 条件候选 | protocol-recovery residual state |
| `EXE-T-<op>-V2` | 保留编号 | 按工具 state；未满足残差门槛前禁止训练 |

## 固定数据

- 训练目标量：2000 行；dev 在训练前冻结；exact-tool coverage 的 test split 与 Full90 永不训练。
- 主来源：`rwkv_lh_exact_tool_coverage_v1` 的 train/dev family，覆盖 18 个本地 operation 和
  final，使用其精确 expected arguments、workspace 和 verifier。
- 原始补充来源计划为 Round1 direct 行，但在任何写出/训练前被固定相似度预检拒绝。按修订 1，
  五个新增 operation 使用冻结 `rwkv_lh_network_exact_tool_selector_v2_4` train/dev family 的
  精确 stage objective，并机械抽取与 Harness 校验参数；test family 完全排除。
- 每个 target 必须通过当前 `ActionDefinition` 参数合同；final 必须包含冻结 verifier 的全部
  required facts。
- split 以 semantic family 为单位。train/dev/test family 交集必须为 0。
- 相似度算法固定 `utf8-byte-5gram-cosine.v1`，比较 canonical task/stage/progress/selected-op，
  同 operation 阈值 `0.95`；运行后不得改阈值。跨 operation 近邻保留并登记。
- 每行保存 source path/SHA、source row/family、prompt/target SHA、selected schema digest、语言、
  stage cluster、禁止字段审计和 target-suffix mask 元数据。

## 训练冻结参数

- 模型：13.3B G1i base SHA-256
  `5d97772ba04a81bdaeba90e1d6d306c70560bf4f784522be61cdcade69e30562`。
- 初始化：zero；禁止从 Stage8 或任何旧 state continuation。
- GPU：物理 0；`CUDA_VISIBLE_DEVICES=0`。
- `peft=state`、`op=fla`、BF16、DeepSpeed stage1、gradient checkpoint、micro batch 1、
  target-suffix loss、BOS 0、ctx2496。
- epoch steps 2000、epoch count 1、`step_save=250`、seed 829；学习率固定为
  `lr_init=2e-5`、`lr_final=2e-6`、`warmup_steps=50`。这些值在第一次训练命令前登记，同一
  run 不得改动；step 250/500/750/1000/1250/1500/1750/2000 均保留，不能只保存最终 state。
- 每个 checkpoint 内容寻址；训练与 serving tokenizer、state tensor、vllm conversion 逐项校验。

## 固定消融与联动

先跑同一固定集合的四格，不根据结果更换数据：

| 组 | Selector | Executor |
|---|---|---|
| `L00` | `SEL-Z0-S39` | `EXE-Z0-V2` |
| `L10` | `SEL-S31-R` | `EXE-Z0-V2` |
| `L01` | `SEL-Z0-S39` | `EXE-G1-V2` |
| `L11` | `SEL-S31-R` | `EXE-G1-V2` |

`SEL-S31-R` 只测差分中的交互项，不能因联动结果晋级。交互量固定为
`(L11-L10)-(L01-L00)`，分别报告 selector exact、Executor contract、E2E Strict 和 wall time。

只有 `EXE-G1-V2` 在固定 dev/canary 上存在同一失败簇至少 3 个可复现错误，条件 state 修复
至少 3 个且不新增其他簇错误，才允许依次增加 `F1`、`R1` 或 `T-<op>`。若 Full90 Strict
相差不超过 1 且硬门槛都通过，选择 profile 更少的组。

## 指标与晋级门槛

### Executor 离线

- raw retention / raw SHA 一致 / selected-operation identity：全部 100%。
- 禁止字段、隐藏 retry、输出 repair、跨 profile state contamination：全部 0。
- JSON parse rate、当前 schema-valid rate不得低于 `EXE-Z0-V2`。
- exact arguments / final required-fact aggregate 至少比 zero 提升 2 个百分点，并且至少 3 个
  zero 错误被稳定修复；任一 operation 的 schema-valid recall 不得下降超过 1 个样本。
- 同输入同 profile 重复 3 次的采样与原始输出按固定确定性配置 byte-identical。

### 当前架构 E2E

- 固定 canary：`B01,B02,B10,M03,M12,H10`，必须 6/6 transport/protocol valid。
- Full90 必须 90/90 valid；G1 Strict 不低于同机 zero，FP/FN 均不恶化；历史 Stage8 只报告，
  不作为放宽门槛的依据。
- selector→executor handoff mismatch、未消费 selection 替换、resume 重选、跨 lane/profile state
  污染均为 0。
- 联网、路径、JSON、命令、异常恢复、项目创建、bug 修复和历史失败簇均进入回归。

### 性能

- 固定报告 Selector 与 Executor 的 TTFT、tokens/s、单步和整任务 p50/p95、GPU 显存、队列和
  state load/copy 时间。
- G1 的质量硬门槛优先；在质量等价时总 wall p95 不得比 zero 恶化超过 10%。

## 停止条件

- 任何数据/源码/模型/profile SHA、GPU、tokenizer、ctx、采样或评价器不一致：该 run 无效。
- OOM 可以用同一预登记参数在清理无关临时服务后重跑；不得偷偷换 GPU、缩短数据或改变阈值。
- 首个通用 state 未通过时，先记录根因和全数据影响，不自动继续堆叠更多 state。
- 完整数据、同类路径、边界、异常、历史回归和实验记录未完成前，不声明问题解决。
