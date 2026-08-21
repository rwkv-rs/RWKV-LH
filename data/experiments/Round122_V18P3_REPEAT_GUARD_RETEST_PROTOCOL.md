# Round122 v18-P3 Identical-Success Repeat Guard 重测预注册协议

日期：2026-08-16（实现前预注册；运行后不得修改口径、门槛或变量定义）

## 决策来源

Round121 按红线回退（Strict 27 < 30），但逐题因果归因（其 MANUAL_CAUSAL_ANALYSIS §三）
显示：**guard 的可归因质量代价只有预注册风险题 H04 一题；−B09/−B14/−B26/+M09 四个
翻转中 guard 均未触发，属单轮采样噪声（实测方差约 ±3）**；可归因收益为 prompt tokens
−43%（18.64M→10.60M）与全部成功循环消除（LH02 195→3 Actions、M17 193→11、
M21 110→15、M28 85→14）。

机械门槛把噪声记在了变量头上。本轮以两项方法论修正重测同一机制：

1. **因果归因门槛**：变量未触发的用例翻转不作为该变量的判决证据。
2. **guard 预算 12→32**：H04 型"坚持后终会分歧"的轨迹需要空间；guard 拒绝不执行
   动作、成本低，总量仍由 max-transitions=200 约束。

## 假设

与 Round121 相同（打破成功循环、大幅降本），另加：预算 32 时 H04 型坚持轨迹有机会
自行分歧；质量对非触发用例中性。

## 精确变更

与 Round121 完全相同的 guard 机制（阈值 3、逐字节相同成功结果、拒绝并回显最近完整
结果、新 causal event `identical_call_repeat_rejected`、`repeat_guard_rejections` 投影、
`RUN_SCHEMA_VERSION=long-horizon.run.v19`），唯一参数差异：
`_MAX_REPEAT_GUARD_REJECTIONS = 32`（Round121 为 12）。Round119 基础全部保留，
无其他任何改动。

## KEEP 门槛（因果归因 + 噪声感知）

1. guard 触发用例中的 Round119-TP 损失 ≤ 1（H04 额度）；
2. Strict ≥ 28（噪声底线）；
3. FN ≤ 2；
4. 90/90 终态完整（0 running、0 空 Final）；
5. prompt tokens < 13M。

全部满足则 KEEP（guard 进入后续轮基础）；任一不满足则回退且该机制不再重测。
期望（非 KEEP 条件）：Strict ≥ 30、H04 在预算 32 下自行分歧、循环题维持低成本。
若 Strict > 31 且 FP ≤ 24 且 FN ≤ 1，不改源码追加 confirmatory Full90。

## 冻结参数

与 Round118–121 完全一致：model `rwkv7-g1i-13.3b-20260805-ctx16384`、endpoint
`http://127.0.0.1:29610/v1`、temperature 0.05、top-p 1.0、top-k 0、penalties 不变、
max-transitions 200、concurrency 1、uv 0.12.5、suite all（90）。

## 流程

1. 重新应用 guard（预算 32）；离线回归（Round121 四项 guard 测试，预算断言更新为
   32）；全量 pytest、catalog 90/90、compileall、`git diff --check`。
2. 冻结只读 source manifest → 运行完整 Full90 一次。
3. 产出 `Round122_v18p3_full90/`：REPORT、results、RUN_PROTOCOL、cases、
   MANUAL_CAUSAL_ANALYSIS（全 90 首次偏离 + 对 Round119/Round121/Round46 flip
   矩阵 + guard 触发归因表 + 固定指标块）。
