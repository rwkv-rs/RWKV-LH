# EXE-G4 dev 评估元数据完整性补充登记

登记时间：2026-08-29（Asia/Shanghai）。首次 G4 joint ablation 已按 fail-closed
停止；本登记发生在任何 G4 R2 arm 运行之前。

## 首次运行失败证据

冻结 G4 runner SHA-256 为
`37a0846bc8ca6aa8add87f1516382f0c33bf6cdac17d5018cb4e3c1dba7f2cb5`。
它完成并保留了 zero-state/G3-dev 的 480 条原始生成，随后在 G4-dev 第 226 条前
由评估器访问 `row["language"]` 时停止。根因是 G4 生成器给 240 条
`synthetic_true_workflow_request_last` 行遗漏了纯评估元数据 `language`；另外 240
条 G3 retention 行已有该字段。prompt、target、selected operation 和训练数据
均未缺失，远端 state 与模型服务也未失败。

首次目录
`run_exe_g4_true_workflow_joint_ablation/` 保持原样，标记为无效的元数据前置失败；
不得删除、覆盖或把部分结果计入选择。

## 固定修复

从冻结 G4 dev source
`a81f3805535649ae75148e0d7debdb3be60e00ba36837b67d0f80fb8113bb50d`
生成一个评估专用、逐行一一对应的 metadata-complete view：

- 已有 `language` 原样保留；
- 缺失时只根据 prompt 是否包含 CJK 字符确定 `zh`，否则为 `en`；
- 预期补齐 240 行，G4 dev 480 行全部得到 language；
- sample id、行序、prompt、prompt SHA、target、target SHA、selected operation、
  source family 及所有其它字段字节语义不变；
- 该 view 只用于评估，不回写训练集，不重新训练 state。

生成后冻结新 view 与 manifest 摘要。R2 仍评估 zero、G3-step2000 和全部 8 个
G4 checkpoint，在原 G3-dev 480 与 metadata-complete G4-dev 480 上使用相同
采样、concurrency=4、schema/canonical/wire/byte-exact 指标和原门槛。选择规则仍为
最早同时通过全部 G3 保留与 G4 workflow gate 的 checkpoint。

并发度、阈值、评价代码、原始响应保留规则均不改变；不修改、补写、重排或隐藏
任何 RWKV 输出。R2 使用新输出目录和新远端 service evidence tag，首次失败证据
保持可复核。
