# Agent Ladder 控制平面整改 V2 预注册

- 日期：2026-08-30
- 状态：实现前冻结
- 基线结果：`NETWORK_SELECTOR_DIVERSE_SOFT_MOE_S66_20260830/run_s66_g3_g6_agent_ladder_v1/BASELINE_RESULT.json`
- 基线 SHA256：`2ce0e62670004827d81a8f5ae408c4308343c53e7a2d98ae912068bd8e2fbf11`
- 固定测试集：`RWKV-LH-AGENT-CAPABILITY-LADDER-V1` 全部 10 题；任务、公开工作区、隐藏验收与阈值均不改。
- 固定架构：强模型只做 Planner/Reviewer；S66 2.9B Selector 只选工具；13.3B Executor 使用任务级 G3/G6；GPU0；本地 vllm-rwkv；不得在单次任务内切换 state。
- 原始输出约束：任何 RWKV 原始输出不得修改、删除、重排、隐藏、截断、替换或作为修复对象。

## 基线事实

- 严格通过 0/10，外部验收 0/10，Agent 完成 0/10。
- 7/10 没有进入 RWKV Executor；其中 5 题终止于本地 Planner/契约语义校验，2 题终止于上游 HTTP 500。
- 3/10 进入 Executor，但均在事务完整性或证据停滞处终止。
- 61 个 RWKV generation 事件的原始输出哈希、UTF-8 字节数和 `postprocessed=false` 全部一致。

## 预注册根因假设

1. 请求路径词法把 `storage.py/service.py` 误识别成单一路径，而不是两个相邻文件名。
2. Adapter 的语义修复循环只运行部分校验；mutation→verify 等完整校验晚到 Controller 才执行，错误无法反馈给 Planner 修复。
3. Planner 提供 `action_budget`，Controller 另行投影 `minimum_actions`，形成双重权威；两根写作用例会生成不可执行预算。
4. Planner 请求 JSON 使用键排序，导致不可变需求和本地修复问题不在输入尾部。
5. 基准报告只统计 provider `supervisor_request_failed`，漏掉 Controller 已持久化的本地语义失败。

## 允许的整改

- 修复通用请求路径提取；禁止按 Ladder task ID、目录名或验收内容特判。
- 提取单一共享契约补丁语义校验器，Adapter 修复循环和 Controller 调用同一实现。
- Controller 机械保证 `action_budget >= projected minimum_actions`，保留 Planner 更大的合法预算，并记录规范化事件。
- 将完整不可变请求放到 Planner/Reviewer 用户负载尾部；修复轮把具体校验错误放到最后。
- 对语义失败建立结构化、可恢复的 Supervisor failure 分类。
- 只增强提示中的既有契约规则，不减弱 mutation 验证、路径覆盖、写作用域、Reviewer 或隐藏验收。

## 禁止项

- 不改变 Ladder 任务、acceptance、阈值或通过定义。
- 不读取隐藏验收来生成 Planner 或 RWKV 输入。
- 不针对固定用例自动补写业务文件、工具参数或答案。
- 不用确定性模块替代 S66 选择或 13.3B 执行。
- 不以修改/过滤 RWKV 原始输出修复任何失败。

## 固定验证顺序与通过条件

1. 单元回归：路径组合、共享语义修复、预算投影、请求尾布局、语义失败报告全部通过。
2. 相关测试：`test_contract_graph.py`、`test_supervisor_openai.py`、`test_capability_projection.py`、`test_hybrid_supervisor.py`、`test_rwkv_e2e_suite.py` 全通过。
3. 全项目测试使用项目内 `--basetemp` 全通过；不得把 WSL/Windows 临时目录错误计为代码失败。
4. 固定控制平面 canary：所有非上游失败题不再因同类路径、预算或 mutation→verify 校验直接中断。
5. 固定 10 题复跑，逐题记录 Planner、Selector、Executor、事务、Reviewer 和外部验收层级；与基线按完全相同布尔指标比较。
6. 原始输出完整性必须为 100%，单任务 state 切换必须为 0，产品服务必须保持健康。

## 指标

- 离散指标：exact boolean / exact event classification，不使用主观评分。
- 文本或结构比较：规范 JSON（UTF-8、递归键排序、紧凑分隔符）的 SHA256 完全相等。
- 原始输出比较：UTF-8 字节 SHA256、字节长度、事件顺序和 `postprocessed=false` 全部完全相等。
- 复跑改进只报告同一固定 10 题的严格通过率、外部验收率、Agent 完成率、进入 Executor 比例及各失败层计数。
