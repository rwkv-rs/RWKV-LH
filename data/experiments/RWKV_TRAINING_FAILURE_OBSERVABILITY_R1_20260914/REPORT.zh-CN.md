# 训练失败现场记录 R1

任务级：没有新增 Agent 验收。统一训练 R2 仍为失败、83 次实际 optimizer 更新、没有导出候选，不能计为 RWKV 能力改善。

已确认工程缺陷：原梯度门只报 missing or nonfinite，丢失具体参数名和当组样本；optimizer 的 finally 清空梯度，外层失败后没有保存现场 State。按种子重放存在浮点差异，不能保证复现原始现场。

改动：所有 State 参数的梯度门保留原有拒绝行为，额外记录缺失/非有限参数、当前累积组各样本真实 loss 与 target token 数；外层在模型已建立的失败中保存原 dtype、未转 BF16 的 State 参数及 SHA。快照失败单列，不替换原训练异常。失败快照没有 profile manifest，不是 candidate，也不含 optimizer moments 或随机数状态，不能宣称完整训练恢复点。

覆盖：缺失梯度与 NaN 梯度均在 optimizer step 前拒绝；CPU 回归验证精确保存、不发布候选且拒绝覆盖已有快照。三个新增回归原代码全部失败，修复后目标22通过。完整1766 passed、0 skipped，328.52秒，见 FULL_GREEN.txt。

边界：本轮仅增强观测，不修复数值异常，不改变 forward、backward、学习率、loss、采样、模型输入或数据标签。正在运行的诊断继续用其事前冻结远端源码。本地 owner 五处修改保留，未上传 GitHub。
