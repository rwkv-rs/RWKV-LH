# S67 Selector state-tuning 预注册

## 触发证据与编号

- zero-state cascade dev result SHA-256：`5b4f9b9477938c49e4c71bc073539a1a53151012b313726d381370bba8641b85`，三个预登记候选全部拒绝；最佳 S67 accuracy/macro-F1 为 `0.906/0.9003777290751903`，低于 `0.96/0.96`。
- state 实验编号：`S67-ST`；checkpoint 编号固定为 `S67-ST500`、`S67-ST1000`、`S67-ST1500`、`S67-ST2000`。
- 只训练 2.9B Selector state；13.3B Executor、Planner、Harness、S66 产品与 RWKV raw 输出均不修改。

## 冻结数据

- train：`rwkv_state_tuning.train.requires_target_suffix.jsonl`，2000 行，SHA-256 `f47864e3e58e437bd5b91e8b52158e3b01accf28292fb99c3f7e0e0a03b85cd0`。
- dev：500 行，SHA-256 `06bec25d03277bd135f59d8d7af745b55bce234900768afebaaf26f121987d13`；不参与 optimizer。
- manifest SHA-256：`0707bd65c64a4a96dd484085abc79c8b5ec199426bb777408ef2671e6be8ea46`。
- target 固定为 `\nSelectorLabelV7: <label>`，BOS `0`，loss 只覆盖 target suffix；`ctx_len=2496`，无 target 截断。
- S67/S65 locked-test 在唯一 dev 候选冻结前继续于 JSON 解析前跳过。

## 远端训练参数

- 远端主机 `rwkv-8222`，物理 GPU0 UUID `GPU-1faf7f09-25f4-2515-b707-6e0766aa841d`；产品端口 `18070` 必须全程监听，实验端口 `18075` 必须空闲。
- 基座 `/home/chase/weights/BlinkDL__rwkv7-g1/rwkv7-g1i-2.9b-20260805-ctx16384.pth`，SHA-256 `ac1ae23d0e65c1d35ba523eacd81a2a4dacb7b886479909bbff34f312e766320`。
- parent state 为 exact zero；`peft=state`、`op=fla`、32 layers、embedding 2560、bf16、DeepSpeed stage 1、micro-batch 1、gradient accumulation 1。
- `epoch_steps=2000`、`epoch_count=1`、每 500 step 保存；seed `1067`；Adam beta `0.9/0.99`、eps `1e-8`；cosine LR `2e-5 -> 4e-6`、warmup 40；data shuffle 开启。
- 训练前必须逐文件校验远端 RWKV-PEFT 源码、基座、数据、validator 与 launcher SHA-256；不得与另一 `train.py` 并发。

## 固定 dev 漏斗

按 500→1000→1500→2000 顺序。每个 state 首先只提取 S67 train/dev mean+last hidden，并训练固定 h128 V2 expert（zero-state C2 的同构结构和优化参数）。screen 门仍为 S67 accuracy/macro-F1 `>=0.96`、每类 recall `>=0.90`。未过 screen 的 state 不提取大规模 retention 特征；这只节省计算，不构成候选选择。

第一个通过 screen 的 state 才进入完整验收；若完整验收失败，继续下一个 checkpoint。完整验收按以下预登记顺序：

1. `ST-FROZEN-CASCADE`：state-conditioned S67 h128 expert + frozen S66-M1 branch + h64 learned gate；raw-logit 公式与 zero-state cascade 相同。
2. 只有 1 未过旧能力门时才运行 `ST-PAIRED-CASCADE`：S67 h128 expert；另一个 h128 retention expert 只用 S65 train state features，目标为真实标签 CE 加 frozen zero-state S66 raw-logit distillation；h64 learned gate 用 S67/S65 两域训练。

两个 cascade 都只有一次 2.9B state-conditioned hidden 提取，没有规则 gate、mask、阈值路由或 argmax 后处理。V2 expert 参数沿用：AdamW `1e-3`、weight decay `1e-4`、dropout `0.05`、batch `256`、最多 160 epochs、patience 30。Gate 参数沿用 C3：AdamW `3e-4`、最多 120 epochs、domain-BCE/MSE/margin 权重 `5.0/1.0/10.0`、margin cap 4。Paired retention expert 固定为 AdamW `1e-3`、同 batch/dropout/epoch/patience，loss 为真实标签 CE + `0.5 *` frozen S66 logit MSE。

## 完整门与选择

- S67、S60、S61、S65 的所有指标、阈值、相似度/argmax 实现与 `ZERO_STATE_CASCADE_HEAD_PREREGISTRATION.md` 完全相同。
- S60/S61/S65 相对 frozen zero-state S66 的 baseline-correct regression 必须分别为 0；S60 每个 source accuracy 不下降。
- generated text、sampling、logit postprocessing、raw-output 修改计数均为 0。
- 选择最早通过 screen 且完整门全过的 checkpoint；同一 checkpoint 优先 `ST-FROZEN-CASCADE`，再 `ST-PAIRED-CASCADE`。一旦选中，后续 checkpoint 不运行；一次 Harness run 内不切换 state。
- 若四个 checkpoint 均未通过，不修改门槛或加入规则补丁，S67 state 记为拒绝并回到数据/模型能力分析。

## 发布边界

唯一 state+head dev 候选冻结并完成 artifact/service 数值一致性后，才允许打开 locked-test，再运行独立端口真实 Harness canary。canary 通过前不替换产品 S66，不停止 `18070/29610`，不删除任何远端或本地 checkpoint、日志、原始 logits/hidden/RWKV 输出。
