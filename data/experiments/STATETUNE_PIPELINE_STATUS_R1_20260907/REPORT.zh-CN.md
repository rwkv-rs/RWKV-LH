# StateTune 数据管线现状与经验整理 R1

轮次：`STATETUNE_PIPELINE_STATUS_R1_20260907`。日期：2026-09-07。执行环境：WSL `UbuntuRecovered`。

## Agent 与角色结果

本轮没有运行 Agent 评测，Strict / completed / mutation / 终止原因均无新增指标。没有角色训练、角色评测、新建角色 datasets、confirmation 重评分或 Holdout 读取/运行。完整代码回归不代表模型能力提升。

## 核查结论与改动

当前工作树没有可运行的完整 StateTune 角色数据生成管线。已核对生产代码、scripts、temp 文件清单与现行规范：旧合成生成链已删除；规范指定的 `rwkv_lh/goal_state_protocols/role_trace_dataset_v1.py` 不存在。退休入口防回归测试列出的 10 个旧源码入口及其对应字节码均未残留。五角色共享 builder 与 LongHorizonStore 是现有基础组件，尚不构成完成逐行 State 上下文重建和数据验收的抽取器。

新增 [StateTune 数据管线源码、现状与经验](../../../docs/STATETUNE_DATA_PIPELINE_STATUS.zh-CN.md)，汇总组件、缺口、未来流程和六条有来源的经验；README 与 HANDOFF 增加入口。新文档的 32 个本地链接均存在。经验区分既有缺陷证据和待实现的数据/比较要求，未宣称训练增益。

用户进一步明确数据生成管线源码也需上传，因此追加全部可达 Git refs 的历史检查与 GitHub 实际核验。旧五角色 G1J v1 的入口、dataset_contract 核心、verifier、来源登记、旧协议与 tokenizer 共 15 个源文件已在 GitHub 保存，远端大小与 Git blob OID 全部匹配本地历史提交 `3f23a6a6fe3e048e3142f43aae4938f92ea5db2c`；新文档给出完整源码入口和依赖关系，记录见 [HISTORICAL_GITHUB_SOURCES.json](HISTORICAL_GITHUB_SOURCES.json)。当前组件随现有分支发布，旧实现按既有清理规范从历史访问，未恢复旧可执行入口。

10 个较新旧入口按原路径在全部已抓取本地可达 refs 中没有历史命中，只有删除清单记录；不能宣称这些源码已上传，也不能由 SHA 重建内容。其他位置是否有副本未确认。历史源码可访问不证明旧数据仍可取得、旧链当前可运行或符合当前生产协议。

核查没有改动生产源码、测试或运行参数。协议 builder、State 生命周期和 checkpoint 导出相关代码、清理报告、trace 可用性报告、轮次对账与现行文档的 SHA-256 均登记于 [AUDIT.json](AUDIT.json)。生成记录的临时脚本按规范位于 temp，逐字节快照保存为 `record_statetune_pipeline_status_r1_20260907.py.txt`，生产代码不依赖它。

## 验证

环境同步与 Chromium 安装均退出 0。完整命令 `.venv/bin/python -m pytest -q tests/`：**764 passed in 60.91s，0 skipped**，包含现有 Torch / State 注入与浏览器回归；原始日志见 [full_pytest.txt](full_pytest.txt)。本轮只整理文档，无代码修复，因此不新增镜像实现的测试或虚构先失败记录。

## 发布范围与边界

用户在本会话明确要求更新到 GitHub。本地当前分支 `chase/rwkv-goal-loop-v2-cleanup` 已跟踪 origin 同名分支，抓取后无远端独有提交，已有 7 个本地提交尚未推送。本轮文档提交追加于其后，并从本地推送该分支；不修改 main。AUDIT 记录推送前提交身份，发布成功与远端 HEAD 核验在会话中报告，本文不提前声称推送成功。

这次发布授权用于现有项目与文档同步，不新增训练或角色数据版本授权。后续仍先修复 Supervisor 合同和基线硬门、同代码完成有效双零，再实现 trace 抽取并按 owner 授权冻结数据与训练。尚未实现的管线与未对账的角色额度继续保留为未完成事项。

## 证据指纹

本轮文件与引用源的完整 SHA-256 见 [AUDIT.json](AUDIT.json)；本轮工件统一校验入口为 [SHA256SUMS](SHA256SUMS)。
