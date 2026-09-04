# 当前 RWKV 输入排列验收

验收日期：2026-08-29（Asia/Shanghai）

## 结论

当前产品架构中的全部 RWKV 分类/生成入口统一使用同一排列：固定协议、工具说明、state、
历史动作和已观察证据在前；当前阶段问题或当前执行要求在最后，随后立即进入 Hidden 提取点或
Assistant JSON 续写点。该规则适用于首轮、后续多阶段和协议拒绝后的重试。

这不是对模型原始输出的后处理。排列只发生在模型调用前；RWKV 返回的 raw text、token IDs、
25 维 Selector logits 和原始 argmax 均原样追加保存，Parser/评分只生成独立派生记录。

## 两条模型边界

1. 2.9B Selector：持久菜单与任务上下文先写入；每一步的有界进度在前，
   `stage_objective` 是 `SelectorStepV4` 的最后字段并紧邻 Hidden 提取点。Selector 只看
   25 个 name/description，不接收参数 schema 或 Executor 文本。
2. 13.3B Executor：任务 state、历史 action/result 与一个已提交工具的完整 schema 在前；
   `current_requirement` 是闭合 JSON 的最后字段，之后立即进入续写锚点。协议拒绝时，精确
   rejection event 成为续写前最后的新问题，不重选工具、不补参数。

## 固定审计结果

- S53 Selector 长链前缀：1,950/1,950 的当前 `stage_objective` 位于末端。
- S54 Selector state-tuning：2,500/2,500 的当前 `stage_objective` 位于末端，且只监督目标后缀。
- EXE-G3 Executor state-tuning：2,480/2,480 的 `current_requirement` 是最后闭合字段；其中
  1,040 条是带 1–5 个历史动作的多阶段输入。
- 冻结真实 S52+G2 canary：34 次 Executor 原始生成输入全部满足；33 次为 request-last，
  1 次为精确 protocol-rejection-last。
- 合计数据输入 6,930 条，运行时 renderer、训练 target 边界和真实生成均通过。

机器可读证据：`REQUEST_LAST_INPUT_AUDIT.json`，SHA-256
`1b0acdab858ac226a29ee755c0db189c301a29b489e331b296daa754262509e7`。
