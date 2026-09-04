# Round93 E2E-B02 人工因果分析

## 结果

- Agent completed：PASS
- External acceptance：FAIL
- Strict E2E：FAIL
- 分类：FP
- Final：非空，且等于 RWKV Final lane 原始输出；但回答错误声称 report.json 已创建。

## 逐环节归因

1. Goal lane 首批只创建读取 input.txt 的 Task。
2. Task lane 成功 `read_file` 后，新的 completion-decision 投影使 RWKV 最终显式调用 `lh_task_done`；Round92 的 read_json 循环已消失。
3. Goal lane收到 input.txt 内容后，RWKV正确提出第二批 Task：创建 report.json，并给出目标字段要求。
4. 第一次致命结构错误：该 Task 的 `after` 使用 `T1-A1`。这是 Attempt ref，不是 Task ref，TaskGraph正确拒绝。
5. 放大环节：Goal protocol correction 仍暴露全部 Goal functions。虽然事件文字要求“纠正上一个调用”，RWKV改为 `lh_goal_done`，Controller也接受了这一不同语义函数。
6. Controller因此只绑定 input.txt 的读取证据就结束 Goal；workspace 中没有 report.json，外部验收失败。
7. Final lane基于错误 completed 状态产生错误完成声明，但文本仍是 RWKV原始回答，Controller没有改写答案。

## 根因

- Goal correction 不是事务性纠错：一次已经明确选择 `lh_tasks` 的结构失败，错误地允许改成 `lh_goal_done`。
- `after` 的接口说明与 TaskGraph能力不一致：说明只提同批 local key，TaskGraph实际也允许已有 Task ref；模型尝试用更细的 Attempt ref表达依赖。

## 已登记整改方向

- 结构纠错必须保留原 semantic function；若拒绝的是 `lh_tasks`，后续只能修正 `lh_tasks`，不能切换为完成或 repair。
- `after` 统一定义为“已显示的既有 Task ref，或同批更早的 local key”；明确排除 Attempt、artifact、未知和未来引用。
- 不删除 `T1-A1`、不映射为 `T1`、不自动创建 Task；所有纠正后的 Task 字段仍必须由 RWKV输出。
