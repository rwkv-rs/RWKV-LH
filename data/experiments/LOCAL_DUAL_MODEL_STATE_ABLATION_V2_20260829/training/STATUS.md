# EXE-G1-V2 训练状态

更新时间：2026-08-29（Asia/Shanghai）

- 状态：物理 GPU0 运行中，尚未完成、尚未晋级。
- 启动 PID 快照：`2665391`。
- 初始化：native zero；命令中不存在 `--state_init`。
- 数据：冻结 2000 行 target-suffix，SHA-256
  `c081d47641d475719d495a0bf3b941f497877eeee2ed85c619a5645a5f7359f7`。
- 参数：ctx2496、BF16、DeepSpeed stage1、FLA、LR 2e-5→2e-6、warmup 50、seed 829、
  step_save 250。
- 输出：`/home/chase/chase/RWKV-PEFT/out/g1i-13.3b-rwkv-lh-exe-g1-v2-2k-zero-lr2e-5-seed829`。
- 日志：`/home/chase/chase/RWKV-PEFT/temp/exe_g1_v2_training/train.log`。
- step250 已落盘并验证：61 个 `[64,64,64]` BF16 tensor 全部有限且各层非零；training 与
  vLLM identity export tensor 完全一致。training/vLLM SHA-256 分别为
  `8f52b08a57405fdba35cc5a567ab6b2c436ed544e5d0a709a16f73f851c538e0`、
  `30407308f464d484c4a4518fd62d4fab5573067f4bd5a5f6dbbc1245a660f0dd`。该 checkpoint 仅为
  已验证候选，尚未选择。
- step500 也已通过相同合同；training/vLLM SHA-256 分别为
  `1f3367f1f0aee4bfa242899727f1a4cbe95cba9e3241530b6e762a23ffd25cec`、
  `efe19b5b18cd6c6f89427da7d47b5ef83c1773b5adec1da630bc82ed40f274cb`，同样未选择。
- 初始化后的观测吞吐约 0.70–0.74 step/s。现有 Stage8 `18070` `/health` 正常。
- 本轮完整项目回归：`uv run pytest -s -q` → 534 passed、1 个 Python 3.13 fork 弃用警告。

完成前不得把任一 checkpoint 标记为 accepted。step250–2000 全部内容寻址并在同一固定 dev480
上评估后，才按预注册门槛选择。
