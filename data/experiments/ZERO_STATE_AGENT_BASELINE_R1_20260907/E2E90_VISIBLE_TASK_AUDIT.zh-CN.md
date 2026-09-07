# E2E-90 可见任务审查

Agent 级：本审查没有运行模型，Strict / completed / mutation / 终止原因均未产生；不报告角色成绩。

只读取 E2E-30、LH12、Extension48 三份可见 tasks.json，共 90 题。不读取 acceptance、Holdout、confirmation，不改题集或评分。分类是按主要交付物进行人工判断，不是原评分体系；逐题原文与分类在 E2E90_VISIBLE_TASK_CLASSIFICATION.json 中可复核。

## 分类口径与结论

- 小型项目补全：要求实现多个协作源码模块、测试、文档和发布工件。已有 scaffold 仍计入此类，不能等同空仓库产品创建。
- 代码修复/扩展：主要目标是修复或补全明确函数/类/已有源码；即使额外生成报告，也优先归此类。
- 多步工作流/故障场景：跨文件迁移、递归发现、多个依赖交付物、分阶段状态留存、重试/恢复/补偿。
- 孤立文件/工具任务：有限文件上直接变换、写入、复制、摘要或哈希；附带 read/write/verify 不自动变成项目。简单选择主/备输入也归此类。

| 套件 | 小型项目补全 | 代码修复/扩展 | 多步工作流/故障场景 | 孤立文件/工具任务 | 合计 |
| --- | ---: | ---: | ---: | ---: | ---: |
| rwkv_e2e_30 | 0 | 5 | 10 | 15 | 30 |
| rwkv_e2e_lh12 | 1 | 2 | 9 | 0 | 12 |
| rwkv_e2e_extension48 | 1 | 6 | 15 | 26 | 48 |
| 合计 | 2 | 13 | 34 | 41 | 90 |

只有 E2E-LH12 和 E2E-H15 明确是多模块 mini-project，均已提供模块 scaffold、REQUIREMENTS 和公开测试；从空仓库创建完整产品的任务为 0。其余 88 题是局部代码修复或受控文件工作流，不能把 E2E-90 总分描述成 90 个真实项目的交付率。多步工作流和孤立任务的边界是本次分类口径，例如 M15/M18 因递归发现归工作流，B04/B26 因直接复制/写固定工件归孤立；不会因此改变原分数或测试身份。

## 典型可见任务

- E2E-B01：`Create greeting.txt containing exactly ...`，写一行文件。
- E2E-B20：`Implement is_even in parity.py ...`，补一个函数，公开测试仅两个测试方法。
- E2E-M24：`Repair queueing.py so TaskQueue rejects duplicate task ids ...`，局部容器行为修复。
- E2E-LH02：明确要求 `at least 15 explicit intermediate checkpoint files`，属于人为规定的长链；可以考察遵守过程约束，不能独立证明自主规划或长程 WKV 记忆。
- E2E-LH09：明确要求 `mock_api`、create→query→update→finalize、固定请求 ID、503 重试及409重放。动作计划已由题干提供。
- E2E-LH12：`Complete the mini-project from REQUIREMENTS.md ... parser.py, analyzer.py, and reporter.py ...`，最接近小型项目交付。
- E2E-H15：event-report 三模块、测试、文档、示例报告和 digest 清单；仍是固定脚手架的迷你项目。
- E2E-M23：从 build_plan.json 按声明内容生成完整 dist tree；这是执行已给计划，不能等同设计/实现新项目。

## 当前生产架构适配

不能断言 90/90 都适配当前 stateful independent-selector。可见题 E2E-LH09 明确依赖 benchmark 专用 `mock_api`；当前生产菜单没有该动作。运行器源码 run_case 中对 independent_selector + enable_mock_api 明确抛 UnsupportedIndependentSelectorOperation，避免把 fixture 动作塞入生产菜单。本审查未读取该题 hidden runner_control，因此这里只证明可见要求与生产菜单的冲突，未读取或确认其隐藏配置。

其余题面没有发现第二个明确要求菜单外专用工具的案例，但逐题的真实恢复行为、隐藏控制与外部验收是否适合当前 per-action State 架构，不能靠可见题静态审查确认。H03/H08/LH04/H17 明写中断/恢复或不得重放，LH11/H13 明写分批检查和 checkpoint；这些是 Harness/ledger/恢复诊断，不能直接解释为 RWKV 跨动作递推能力。

## 公开答案和过程提示

本审查没有发现或声称读取隐藏 acceptance 泄漏。公开单元测试本身是合理的开发输入；但部分可见 verifier 已直接写出该固定输入的完整最终工件值，使“从输入推导结果”退化为抄录公开 expected 的风险确实存在。例如：

- E2E-H10 的 verify_release.py 直接列出所有 item totals、grand_total=40.5 及报告行。
- E2E-LH01 的 verify_release.py 直接给出完整 expected release object。
- E2E-M30 的 verify_config.py 直接给出完整迁移后 config 与 migration_report。
- E2E-H11 的 verify_pipeline.py 直接给出完整 expected release object。
- E2E-H18 的 release_validator.py 直接给出完整 products.json 与报告行。

这些是可见的 oracle 式答案提示，不是通过本次审查证实的隐藏信息越界；能通过它们不充分证明对未知输入泛化。题面还公开了指定阶段、策略、文件列表和固定返回码（尤其 LH02/LH09/LH11/H13），从而降低自主设计与规划难度。应保留其机制诊断定位，不能作为新项目生成能力的唯一基线。

## 建议的使用边界

E2E-90 继续作为原有冻结的回归/机制诊断题集；若产品目标是“创建某项目并实现一组功能”，应另行预注册项目级可见任务规格，以功能目标、初始仓库、环境约束和外部验收为核心。不能运行后删除失败 fixture、改题或重新解释 E2E-90 分母。新增正式题集、角色数据版本或训练需遵守 owner 授权和训练轮次限制；本审查未新建 data/datasets 目录。

## 来源 SHA-256

- `benchmarks/rwkv_e2e/rwkv_e2e_30/tasks.json`：`0bf73c9a86bd014f5a94e5686ffe744bbef6c560f4227e37d0b753b900481c4c`
- `benchmarks/rwkv_e2e/rwkv_e2e_lh12/tasks.json`：`d813a7bc3a42e27ee3573ea342a918bd7ee5347ca8b0e893c04fded262457a5e`
- `benchmarks/rwkv_e2e/rwkv_e2e_extension48/tasks.json`：`384d52b5395dbcb31947dbfd1cfe63167ccbe68ed8b03e675fddc32ffd25ec7b`

## 全量分类

| 类别 | Task IDs |
| --- | --- |
| 小型项目补全 | E2E-LH12, E2E-H15 |
| 代码修复/扩展 | E2E-B10, E2E-M02, E2E-M09, E2E-H01, E2E-H07, E2E-LH01, E2E-LH10, E2E-B20, E2E-B30, E2E-M12, E2E-M20, E2E-M24, E2E-H11 |
| 多步工作流/故障场景 | E2E-M01, E2E-M04, E2E-M06, E2E-M10, E2E-H02, E2E-H03, E2E-H05, E2E-H06, E2E-H08, E2E-H10, E2E-LH02, E2E-LH03, E2E-LH04, E2E-LH05, E2E-LH06, E2E-LH07, E2E-LH08, E2E-LH09, E2E-LH11, E2E-M11, E2E-M14, E2E-M15, E2E-M16, E2E-M17, E2E-M18, E2E-M23, E2E-M28, E2E-M30, E2E-H12, E2E-H13, E2E-H14, E2E-H16, E2E-H17, E2E-H18 |
| 孤立文件/工具任务 | E2E-B01, E2E-B02, E2E-B03, E2E-B04, E2E-B05, E2E-B06, E2E-B07, E2E-B08, E2E-B09, E2E-M03, E2E-M05, E2E-M07, E2E-M08, E2E-H04, E2E-H09, E2E-B11, E2E-B12, E2E-B13, E2E-B14, E2E-B15, E2E-B16, E2E-B17, E2E-B18, E2E-B19, E2E-B21, E2E-B22, E2E-B23, E2E-B24, E2E-B25, E2E-B26, E2E-B27, E2E-B28, E2E-B29, E2E-M13, E2E-M19, E2E-M21, E2E-M22, E2E-M25, E2E-M26, E2E-M27, E2E-M29 |
