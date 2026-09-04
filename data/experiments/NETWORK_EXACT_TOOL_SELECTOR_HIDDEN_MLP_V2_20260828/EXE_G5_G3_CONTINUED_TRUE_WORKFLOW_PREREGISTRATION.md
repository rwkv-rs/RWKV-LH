# EXE-G5：从 G3 继续训练的单一合并 Executor state 预登记

登记时间：2026-08-29（任何 G5 训练或 checkpoint 生成之前）。

## 已观察根因与假设

G4 从 zero state 在固定 2,000 行混合数据上训练。step250–2000 全部完成双 dev480 raw-first 评测。新增集从 264/480 上升到 447/480，真实 workflow 相对 G3 最终救回 116、回退 0；但 G3 保留集最终只有 403/480，八个 checkpoint 均未同时通过双 480，因此 G4 被拒绝。

这证明 workflow 数据有效，但从 zero 同时重建既有 G3 能力与新增能力会遗忘。G5 的固定假设是：以已经通过 G3 dev480 的 G3 step2000 训练态作为唯一初始 state，再以较小学习率继续训练同一混合集，可以把联动写入一个 state。部署时仍在 Executor lane 创建时只加载一次，不在阶段间切 state。

## 固定输入与训练

- 基础模型 SHA-256：`5d97772ba04a81bdaeba90e1d6d306c70560bf4f784522be61cdcade69e30562`。
- parent training state：G3 step2000 `rwkv-step-2000.pth`，SHA-256 `9f22ce1ef1b71a157f966e4abeb1ef0ef67014bc9fd26f86106857f23b01e016`；必须通过 61 tensor、BF16、有限、非零与显式 `state_init` attestation。
- 数据：冻结 G4 train2,000/dev480；train SHA-256 `5bb2e09f4e9f109438acadc703c3ccb1d49051fee5db0b548e9584e26910e593`，manifest SHA-256 `ad0781511f2ebc57b30a44dc7cb82daccf43f9871de7d36bcdbd58aeae9c831f`。
- 数据比例保持 1,200 条 G3 direct retention + 800 条 true workflow，不增删、不按失败用例改标签。
- 物理 GPU0；target-suffix loss；BOS 0；ctx2496；batch1；BF16；PEFT state；FLA；2,000 steps；每250步保存。
- seed1063；LR `5e-6 -> 5e-7` cosine；warmup40；Adam beta1 0.9、beta2 0.99、eps1e-8。

## 固定评测与选择

按 step250、500、750、1000、1250、1500、1750、2000 顺序，在同一物理 GPU0、temperature0.1、top-p1、top-k0、单次 raw-first 下评测冻结 G3 dev480 与 metadata-complete G4 dev480。所有点都运行完；选择最早同时满足以下条件的 checkpoint：

1. 两个 dev 各自 transport、response envelope、schema、operation、canonical call、wire arguments 与 byte target 全部 480/480；
2. G4 每个 operation canonical recall >=0.95；
3. 相对 G3 的 240 条 true-workflow 子集，rescued >0 且 regressed=0；
4. state、模型、GPU0、raw token/output 和 append-only journal attestation 全部有效。

没有通过候选时 G5 不发布，也不放宽门槛。通过后才进入 S53/S60 × G3/G5 真实 2×2 消融；优先选择 state 数最少的 S60+G3，只有 S60+G5 独立达到 6/6 且完整性通过时才选择 G5。原始 RWKV 输出不得被诱导、修改、删除、重排、隐藏或由控制器语义替换。
