# Round54 Canary 因果分析

状态：固定 15 题 canary 已结束；结果 `0/15`。由于控制组和目标组均出现同一结构性退化，本轮按预注册门槛提前淘汰，不运行 E2E-90。源码与测试已回退。

## 固定结果

| Case | 终态 | Task 数 | 模型请求 | 关键终止原因 |
| --- | --- | ---: | ---: | --- |
| B01 | interrupted | 202 | 201 | 199 次 refine、0 次 execute，达到 transition limit |
| B02 | interrupted | 477 | 201 | 递归细化，达到 transition limit |
| B10 | interrupted | 664 | 201 | 递归细化，达到 transition limit |
| M01 | interrupted | 770 | 201 | 199 次 refine、0 次 execute |
| M03 | not_created | 0 | 1 | Goal 阶段 JSON 不完整 |
| M06 | interrupted | 818 | 201 | 递归细化，达到 transition limit |
| H02 | blocked | 580 | 136 | 132 次 refine 后 atomicity schema 失败 |
| LH01 | interrupted | 204 | 202 | 递归细化，达到 transition limit |
| LH02 | interrupted | 493 | 201 | 已原子 checkpoint 结构被反复细化 |
| LH11 | blocked | 18 | 16 | 子 Task 未全部汇入模型指定出口 |
| M12 | blocked | 28 | 8 | 子 Task 未全部汇入模型指定出口 |
| M16 | blocked | 5 | 4 | atomicity schema 字段错误 |
| M18 | interrupted | 207 | 219 | 递归细化，达到 transition limit |
| H12 | blocked | 130 | 33 | 反复细化后协议/图约束失败 |
| H13 | interrupted | 246 | 201 | 原子 list Task 被反复细化 |

## 最早共同偏差

RWKV 能在自然语言 reason 中正确识别原子性，却不能稳定提交对应结构化 decision。B01 的首个和后续输出均为：

- `decision="refine"`；
- 返回一个与父 Task 等价的单子 Task；
- reason 明确写“Task is atomic”“single atomic action”“No refinement is needed”。

B01 全程产生 199 个这样的 `refine`，没有一次 `execute`。H13、LH02 的单次 read/list/checkpoint 也出现相同矛盾。M01、M06、H02 等真正复合 Task 虽然能产生多阶段子图，但新子 Task 又从 Goal 语境重新展开整项工作，而不是只保留自己的局部 contract，因此递归放大：M01 最终 770 Tasks，M06 818 Tasks。

这验证了一个更深的接口问题：弱模型在多选枚举字段中会保留 prompt 的默认/高显著值，同时在自由文本中表达相反判断。Controller 若根据 reason、子 Task 数量、标题相似度或“看起来已经原子”把 `refine` 改成 `execute`，就是规则替 RWKV 改决定；本项目明确禁止该做法。

## 对下一步的约束

1. 不再增加独立的 pre-action meta decision、judge 或 reviewer；Round53 和 Round54 分别证明同源复核会自我确认，而枚举式原子判断会自相矛盾。
2. 根因仍是现有硬约束 `one Task = one action`。更直接的结构应允许 **同一个 Task 内由 RWKV连续执行多次 action**，而不是先要求 RWKV重写 Task 图。
3. 可复用现有 post-action Task commit：将它从 `pass|replan` 扩展为 `complete|continue|replan`。`continue` 只表示 RWKV认为当前 Task postcondition尚未满足，保留同一 Task、已观察 output 和 workspace state，随后由 RWKV生成下一个完整 action。Controller不拆 Task、不选 action、不补参数。
4. 为避免又出现额外 meta-call，下一变量必须复用已经存在的 post-action semantic commit，而不是新加一层请求。效率不是门槛，但减少冲突状态机本身有利于质量。
5. 外部验收和 frozen reference 仍只在运行后分析；不得用 hidden criterion 驱动 continue/complete。

Round54 是完整的否证实验，不上传为最佳架构。当前远端最佳仍为 Round46 commit `14d864d`。
