# G1J zero-State 基线重复次数修订

修订时间：2026-09-03（Asia/Shanghai）

## 修订依据

用户在主基线尚未完成时明确要求将三轮重复改为一轮，以缩短真实 Agent 基线建立时间。该修订发生在最终汇总与 StateTune 之前，不依据某一用例得分选择更优重复。

## 新的正式分母

- B01–B14 只使用原编排顺序中的第一轮、预登记 run label `20260903`，共 14 个有效结果。
- P01–P07 各运行一次，共 7 个有效结果。
- 完整主基线共 21 个有效结果。
- run label 只用于实验目录与身份记录，不作为 seed 或路径提示发送给模型。

## 不变项

- 每个 B 用例仍使用 240 transitions 总预算与原先冻结的唯一 PromptV1 / Tool Call JSON 格式。
- 模型、zero State、Head、工具定义、Planner、Stage Checker、请求参数、转换层、独立外部验收、阈值和评分算法均不改变。
- 仍只有 G1J `final_answer` 才是 Agent 完成信号。
- 基础设施失败和被外部中断的尝试继续完整归档，不进入能力分母。

## 既有额外运行

- 已完成的 `20260902` B01–B03 保留为补充观察，不进入新的 21 项主基线分母。
- `20260902` B04 的主机重启中断尝试继续保留在 `infrastructure_invalid/`，不再要求补跑。
- `20260904` 不再运行。

## 生成方式

本修订由用户在当前基线任务中直接提出；单轮编排由 `temp/run_g1j_zero_public_canary_single_round_v1_20260903.py` 执行，单轮 B 组汇总由 `temp/aggregate_g1j_zero_public_single_round_baseline_v1.py` 生成。
