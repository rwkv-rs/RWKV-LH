# 开发评测收尾的可选题集依赖修复

Agent 级：本修复没有新增模型调用、Strict、completed、mutation 或终止原因结果。R4 原始尝试由主代理标记 INVALID_HARNESS_DEPENDENCY，不能用修复后的代码重评分、接续或补考；后续运行须另行冻结。本记录只报告 runner 回归，不表示模型能力通过。

根因是 `run_case()` 在隔离验证器返回后、写出 model_trace 和完整 audit 之前，遍历全部 SUITES，用 `suite_resources(definition)` 获得每份 acceptance 文件路径。这一函数调用 `importlib.resources.files()`，因此生成一组禁止泄漏的路径字符串却隐含导入全部题集包。任意未选择的可选包缺失，都能让当前正常执行题目在收尾阶段抛出 ModuleNotFoundError；问题适用于所有选中题集和共用该收尾段的 Controller 架构，不仅是 R4 首题。

上游题目和模型可能已经执行、外部验证也已经结束，但收尾异常阻止完整 trace/audit 写出，随后外层通用 runner_error 记录不能代表这些模型能力。该依赖也使独立 checkout 错误地要求安装不参与本轮的题集。不能以复制封存包、删除相应 denylist 项、跳过泄漏检查或降低 Strict 阈值来绕过。

本轮只修改 `scripts/run_rwkv_e2e_benchmark.py` 和 `tests/test_benchmark_protocol_boundary.py`。新增 `suite_resource_paths()`，从 runner 所在文件系统 checkout 根目录及 SuiteDefinition.package 的路径分段构造 tasks/acceptance 身份，不导入、打开或检查该题集包是否存在。全部 SUITES 的 acceptance 路径仍进入原 denylist，序列化 trace 后的原字符串匹配和 Strict 公式保持不变。登记不存在的包也保留其禁止路径。

同类路径已整体核对：`load_suite()` 与 `_write_run_metadata()` 只处理显式选择的题集，继续使用原 `suite_resources()` 加载实际内容；模块顶层默认 core30 两个资源常量也有无条件导入问题，一并改为纯路径身份。修复后 `importlib.resources.files()` 只留在真实读取选中题集的函数内，不增加 find_spec、可选包导入或缺失忽略分支。

新函数遵循 runner 已有的文件系统 checkout 布局；运行 metadata 原本就以该根目录做 relative_to。6 个公开安装题集（core30、lh12、extension48、agentv1、agentladderv1、realprojectdevv1）的新旧 tasks/acceptance 路径字符串逐项相同。未读取或复制封存题集内容；此修复不引入 zip/out-of-tree 资源部署支持，也不改变选中题集缺失时应失败的行为。

先新增测试后运行旧实现，`RED_TESTS.log` 为 10 failed、5 deselected：6 项纯路径接口/既有字符串等价、1 项导入 runner 不加载默认题集，以及 3 项实际 run_case 收尾回归。后 3 项真实重现资源导入异常；运行输入是人工普通测试任务，模型、Controller 完成与外部验收是明确 mock，不是角色协议输入或生产 trace。Store、workspace 初始化与收尾导出使用实际代码，测试没有发模型请求。

首次修复后，12 项已通过，3 项暴露测试 fixture 的 `Store.save()` 遗漏必需 causal_event；这次记录保留为 `GREEN_ATTEMPT_1_FIXTURE_CAUSAL_EVENT.log`。fixture 随后使用生产 `CausalEventDraft.create()` 显式保存 mock run_completed 事件，没有修改生产判定。

最终定向结果 `GREEN_TESTS.log`：**15 passed in 0.35s**。新增 10 项覆盖：全部公开路径字符串不变、模块导入不触发任意题集资源加载、可选包缺失仍能导出完整病例 audit/model_trace、普通输出在其余明确 mock 条件满足时通过、已安装题集路径泄漏仍失败、缺失可选题集路径泄漏也仍失败。既有只读 metadata 5 项同时通过。完整 tests/ 由主代理随后运行并记录，本文不预填最终数字。

生产和测试文件已停写，未修改 `rwkv_lh/`、角色协议、预算、State、评分阈值或旧冻结材料；没有训练、角色数据生成、服务器 Git 或提交。代码、红绿日志与本报告 SHA 见同目录 `SOURCE_SHA256.json`。
