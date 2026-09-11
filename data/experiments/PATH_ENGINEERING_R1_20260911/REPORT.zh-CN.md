# 路径工程轮（2026-09-11）

单主题：把"知道路径"从模型职责转为工程职责（owner 决定：直接做，含提示词；Planner 提示词不强调路径，只保留隔离工作区框架）。不改角色协议、不改评分、不改数据门。

## 改动

1. **确定性别名归一**（rwkv_lh/harness.py `_normalize_path_literal`，进入 `resolve_path`）：吸收已知传输伪迹——成对引号、反斜杠分隔符、`./` 段、沙箱挂载别名 `/workspace`（bubblewrap 内命令真实观察到的绝对路径，是实际别名而非猜测）。除这些精确重写外一律不动；scope 校验顺序不变，越界仍 fail-closed（新测试覆盖 `../`、`/etc/passwd`、`/workspace/../` 三类逃逸）。
2. **未命中的结构化近邻证据**（`_nearest_workspace_paths`）：must_exist 解析失败时，错误消息附带工作区内最接近的真实路径（先精确 basename 匹配、次 stem 包含；确定性排序、上限 5 条、扫描上限 5000 项）。**绝不静默纠正**——只把可选字面量放进修复反馈。异常类型保持 `FileNotFoundError`，下游 outcome 分类仍为 `not_found`（初版误改为 HarnessError 使分类变 invalid，被 test_parallel_atoms 既有测试当场抓住，已修正——这正是该分类合同存在的价值）。
3. **工具 schema 描述**：14 处 `"relative path"/"relative directory"` 统一为 "path/directory relative to the workspace root"——Executor 每次看到的参数描述都声明基准。
4. **Planner 提示词**（supervisor_openai.py）：按 owner 要求只加一句 "All work happens inside one isolated task workspace; the runtime resolves every path within it."，不加任何路径机制说明。

## 验证

全套 pytest **1480 passed、0 failed**（1479 + 1 新测试；中途一次真实回归被既有测试拦截并修正，保留在过程记录中）。

## Waiver 影响

本轮改动 `rwkv_lh/harness.py` 与 `rwkv_lh/supervisor_openai.py`——**已并入待签的 SELECTOR_EQUIVALENCE_RENEWAL_R3 范围**（该续签本就因 R3 冻结修复待重签，本轮不新增签署次数，但签署必须 pin 本轮之后的最新 SHA）。
