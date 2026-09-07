# 唯一协议与旧数据链清理 R1

轮次：`PROTOCOL_DATA_CHAIN_UNIFICATION_R1_20260907`。执行环境：WSL `UbuntuRecovered`。日期：2026-09-07。

## Agent 级结果与结论边界

本轮没有运行真实模型 benchmark。Strict、completed、mutation 数和 Agent 终止原因均无新增结果；没有训练、创建角色数据集版本、重评分 confirmation 或运行最终 Holdout 验收。不能据单元测试通过推断 Agent 能力提升。

当前五个角色均已收敛到各自唯一的协议模块和共享输入构造入口，旧协议、兼容入口、旧合成数据链、旧数据和旧实验已从工作树直接删除。最终完整代码回归：**666 passed in 53.50s，0 skipped**。本轮完成代码统一、清理和文档更新；当前代码的远端 attestation、两遍 all-zero 基线及 Agent 级验收仍待独立执行。

## 根因、范围与整改

1. **角色协议来源不唯一。** 当前 Executor 模块依赖旧版实现，Selector / Auditor / Finalizer 的输入在调用方和测试中另行拼装；运行身份也存在硬编码。现保留 Selector v4、Executor v4、Step Auditor v3、Finalizer v1、Final Auditor v2 五个协议模块，各自拥有 schema、prompt prefix、`build_prompt_source()` 和 renderer；Controller、生产模型输入、预算估算与测试均调用共享构造入口。尚未实现新的 trace 数据抽取器，因此不宣称新的 StateTune 数据链已经可用。
2. **独立 Executor 存在并行协议路径。** 旧的 request-last 披露与重试格式绕过当前输入，fork 丢失强制协议标记。现删除旧路径，要求完整当前输入，bootstrap / append / rollover / generate / commit / fork 均维持协议要求，HTTP 与 native 两种传输均覆盖。预算估算使用实际 execution state 与事实，避免估算与发送内容脱节。
3. **协议帧检测把数据内容当控制边界。** 简单搜索旧标签会拒绝合法引用，查找最后一个当前前缀也会被数据内文本误导。现按帧位置解析 JSON，并校验到最后 Tool Call anchor 的边界；引用历史标签、引用伪造完整帧、真实尾部未知帧及重试均有回归。没有保留旧版解析器或 identity stub。
4. **旧数据链仍能执行，常规测试边界不清。** 删除旧合成生成、组装、角色评测入口及仅服务旧数据链的测试，清理对应孤立字节码。完整回归需要 Torch，测试工件统一到 `data/test_runs/`，原生运行缓存使用 `data/runtime/`，当前生产代码不依赖临时分析目录。
5. **普通 provenance 采集会越界读取未选择的题集。** benchmark 的源码 manifest / git diff 改为仅覆盖源码范围，题集资源只随明确选择的 suite 收集；`all` 仅扩展正式 E2E-90 集合。独立 Selector 的 Executor 身份引用当前模块常量。回归使用假的资源和读取哨兵，没有读取真实 Holdout。
6. **文档和页面把历史结果当作当前状态。** README、AGENTS、HANDOFF、统一规范和 Web 状态同步当前 v7 架构及角色 State 生命周期，移除过期成绩，明确新代码尚待 all-zero 基线；Selector 已满三轮，Executor / Step Auditor 轮次登记冲突须 owner 对账，不自动授予训练额度。

整改涉及角色输入的上游构造、推理会话、Controller 披露、原生 Selector 身份、下游工具参数及验收元数据。Controller 的业务职责没有扩展，不读取隐藏 acceptance 或重写 Final，没有添加外置 Head、用例路径特判或额外模型调用。

## 删除与保留边界

按 owner 最新指令，旧内容直接删除，不建 retired/archive，也不保留 stub。主删除清单记录 **6,627 个文件，6,915,098,162 字节**，包括 16 个旧角色数据目录、既有实验目录和旧临时驱动；独立入口/字节码清单另有记录，不能与主清单混为同一计数口径。记录只保存文件路径、大小、SHA 和验证证据。GitHub 中已存在的历史由 owner 查询，未跟踪的旧文件不会因本次删除自动进入远端历史。

Real Agent Holdout V2 是仍有效的封存验收资产，不属于退役训练数据链。其题集/数据原位置保留；冻结登记目录和来源目录使用目录 rename 移至 `data/acceptance/`，未枚举或读取其中内容。相关验收测试移至 `acceptance_tests/`，本轮未执行。已删除重建题集和重算相似度的旧入口；将来最终验收的冻结 source SHA 仅对照删除清单，不重算或调整冻结相似度。

清理前工作树已有未提交的当前架构、Controller、原生 Selector 等改动。本轮在该工作树基础上统一并完整验证，没有回退这些改动；本地提交包含构成当前可运行源码所需的完整改动。封存的未跟踪验收资产不读取、不纳入本轮提交。

## 验证证据

先失败后通过的证据按问题保存：

| 问题 | 首次失败记录 | 修复验证记录 |
|---|---|---|
| 共享构造、Selector 前缀与目录唯一性 | `role_builders_red.txt`、`selector_prefix_red.txt`、`inventory_red.log` | `role_builders_selector_green.txt`、`root_integration_green.log` |
| Executor 当前输入与披露/预算 | `executor_red.log`、`executor_legacy_session_red.log`、`executor_entry_budget_red.txt` | `executor_green.log`、`executor_legacy_session_green.log`、`executor_entry_budget_green.txt` |
| 引用文本与协议帧边界 | `quoted_old_marker_red.log`、`executor_framing_red.log` | `executor_framing_green.log`、`full_pytest.log` |
| fork 继承协议要求 | `executor_fork_red.log` | `executor_fork_green.log` |
| 旧入口和孤立字节码 | `LEGACY_ROLE_CHAIN_RED.log`、`LEGACY_ROLE_BYTECODE_RED.log`、`orphaned_protocol_bytecode_red.log` | `LEGACY_ROLE_CHAIN_GREEN.log`、`LEGACY_ROLE_BYTECODE_GREEN.log`、`full_pytest.log` |
| 页面状态与运行缓存 | `current_status_and_cache_red.log` | `root_integration_green.log` |
| 未选题集读取边界 | `BENCHMARK_METADATA_RED.log` | `BENCHMARK_METADATA_GREEN.log` |

环境通过 `uv sync --frozen --offline --extra selector-runtime --group dev` 使用本地缓存补齐 Torch 等依赖。最终验证命令严格为 `.venv/bin/python -m pytest -q tests/`，结果见 `full_pytest.log`。此前完整回归 `full_pytest_initial.log` 为 662 passed / 2 failed：两项失败是中间版本拒绝报错文本与断言不一致，最终版本保留明确的协议要求提示后重新完整运行通过。`role_builders_production_basetemp_setup_error.txt` 记录了测试工件父目录缺失的中间环境失败，现通过纳入 `data/test_runs/.gitkeep` 解决。没有隐藏失败日志或把未完成运行计为通过。

`MANIFEST.json` 记录本轮边界、最终测试、当前源码和证据指纹；`SHA256SUMS` 提供统一复核入口。子任务指纹是其阶段快照，最终源码以本轮主 manifest 为准。

源码、配置和文档的 `git diff HEAD --check` 通过。原始 pytest 失败日志包含框架输出的行尾空格，按原字节保留，不为格式检查改写证据。

## 回归风险与后续边界

当前输入、Executor 会话约束和预算估算均有变化；旧训练 State 和旧远端 decoder manifest 不能自动认定与新输入匹配。后续模型运行须按当前代码重新 attestation，两臂使用相同代码，不重用历史结果作为当前比较臂。现有单元测试涵盖公共协议、Controller、两种推理传输、恢复和异常路径，但不替代真实模型运行或最终验收。

后续工作以 `docs/HANDOFF.zh-CN.md` 和统一规范为准：先固定代码做 all-zero 基线，再从生产 trace 建立统一角色数据流水线；新数据版本、训练和最终 Holdout 不在本轮执行范围内。
