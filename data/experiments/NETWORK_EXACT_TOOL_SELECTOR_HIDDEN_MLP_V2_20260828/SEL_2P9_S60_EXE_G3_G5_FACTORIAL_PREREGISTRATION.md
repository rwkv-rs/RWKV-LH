# S60 × G3/G5 真实 Harness 固定 2×2 因子消融预注册

登记时间：2026-08-29；发生在 S60 Head 训练完成、G5 checkpoint 评测以及本轮任一真实 Harness arm 之前。

## 目的与固定因素

本轮只分离两个因素，不改变 Harness、工具合同或评价器：

1. Selector 布局：冻结保留基线 S53（V4 request-last）与候选 S60（V7 literal requirement byte-tail）。两者都使用同一个 2.9B zero-state、Hidden concat(mean,last)、h64 MLP 和 raw 25-logit argmax；不生成 Selector 文本，不做阈值、重选或 logit 后处理。
2. Executor state：冻结保留基线 G3 step2000 与候选 G5。G5 只有在预注册的 G3/G4 双 dev480 全检查点消融产生合格候选时才可进入；不得以 G4 或其他 state 代替。

四个固定 arm 按顺序运行：S53+G3、S60+G3、S53+G5、S60+G5。若 G5 无候选，两个 G5 arm 明确登记 unavailable，仍运行两个 G3 arm，不补选其他 checkpoint。

## 固定真实用例与配置

- 用例保持上一轮已经冻结的 6 个真实 Harness case：`E2E-B01`、`E2E-B02`、`E2E-B10`、`E2E-M03`、`E2E-M12`、`E2E-H10`；不依据 S59/G4 的失败内容增删或改写。
- 13.3B：物理 GPU0、temperature 0.1、top-p 1、top-k 0、单次原始生成；只向 Executor 披露被选中的一个参数 schema 与当前执行目标。
- 2.9B：本地物理 GPU0、zero initial state、同一 forward 的 mean+last；服务只接收 25 个名称/描述、bounded progress、stage role、current stage 与 immutable requirement。
- 每个 Selector lane 和 Executor lane 各自创建并只加载一次 state；不在阶段间切换 state。
- 每个 arm 必须保留完整原始响应 envelope、raw text/token、Selector raw logits、state attestation 与 append-only journal。不得诱导、修改、删除、重排、隐藏或语义替换 RWKV 原始输出。

## 固定完整性门槛

每个 arm 同时满足以下条件才 eligible：

1. 6/6 strict verifier 通过；
2. `generation_inputs == raw_generations`，且每次输入满足 current requirement 或 protocol rejection 位于续写边界；
3. committed Selector outputs 与请求数一致；S60 每个 checkpoint 的 V7 顶层最后字段为 `current_question`，其嵌套最后字段为 `complete_requirement`，并且 literal requirement 与 immutable task 完全一致；
4. 无隐藏 retry、无 logit 后处理、无原始输出修改或删除；
5. Selector/Executor 模型、Head、state、GPU0、采样配置和输入协议身份全部匹配运行前冻结的执行身份补充登记。

## 指标、因子效应与选择

以每个 arm 的 strict pass 数（0–6）登记：

- Selector 主效应：`mean(pass(S60,G3), pass(S60,G5)) - mean(pass(S53,G3), pass(S53,G5))`；
- Executor 主效应：`mean(pass(S53,G5), pass(S60,G5)) - mean(pass(S53,G3), pass(S60,G3))`；
- 联动：`pass(S60,G5) - pass(S60,G3) - pass(S53,G5) + pass(S53,G3)`。

发布只允许 requirement-byte-tail 的 S60：优先选择 S60+G3（最少新增 Executor state）；只有 S60+G3 未通过且 S60+G5 独立达到 6/6 时才选择 S60+G5。S53 只作保留基线，任何 S53 arm 都不得发布。没有候选时保持现有产品配置，不修改 `.env.local`。
