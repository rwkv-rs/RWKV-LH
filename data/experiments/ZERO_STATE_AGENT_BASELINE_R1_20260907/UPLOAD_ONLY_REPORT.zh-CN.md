# 服务器仅接收本地上传：部署身份整改记录

日期：2026-09-07。记录范围：落实 owner 的“服务器上不能使用 Git，只能本地上传”，修正运行身份依赖并整理 R2 双零准备证据。本报告仅在本地读取源码与已落盘记录、写入新报告和证据 SHA 清单；未执行远端命令、模型推理、训练，也未读取 Holdout。

当前没有有效的 Agent Strict / completed / mutation / 终止原因基线分数。首次 `real_project_zero_a` 已中止并标 INVALID，B 臂未启动；原尝试的成绩、噪声估计、训练来源资格均为 false，原始证据保留。[INVALID_ATTEMPT_01.json](INVALID_ATTEMPT_01.json) 记录了约束、退出过程和原冻结 SHA。部署回归通过不能替代模型能力评测；本报告也不提供角色能力分数。

## 根因、影响与修改边界

原生 Selector 的启动链为 `native_network_service.main()` → `PersistentVLLMRWKVExtractor` → `LocalVLLMRWKVExtractor._load_base_identity()`。底层身份构造原先依赖 engine 目录的 Git revision 与 working-tree 状态。这使一个通过 rsync/SCP 上传、没有 Git 元数据的完整 engine 不能按原方式启动或证明身份；远端冻结核验脚本同样依赖 Git 查询。问题位于共用的 engine 身份层，会影响所有复用该提取器的路径，不能只删掉一次 SSH 预检中的 Git 命令。

当前 [local_backend.py](../../../rwkv_lh/state_router/local_backend.py) 增加成对的 `engine_source_manifest` / `engine_source_manifest_sha256` 设置及统一 `_validate_engine_source_manifest()`。先验证 manifest 自身 SHA、schema、engine 根路径、声明 revision 和规范化相对路径，再比较整个范围内的文件集合、每文件 SHA-256 与字节数。`engine_identity_backend=uploaded_source_manifest` 明确身份依据；`engine_dirty=None` 表示未查询 Git，不能改报为 Git clean。声明的 revision 是来源标签，当前内容身份来自实际文件清单。

[native_network_service.py](../../../rwkv_lh/exact_tool_selector/native_network_service.py) 将两个清单参数传入相同底层设置；[上传后的 Selector launcher](UPLOAD_ONLY_SELECTOR_LAUNCHER.json) 已显式绑定路径与 SHA。[远端核验脚本快照](SOURCE_SNAPSHOTS_R2/attest_current_zero_remote_r1_20260907.py.txt) 使用同一个清单验证函数和文件散列，服务状态读取使用 systemctl，没有远端 Git 调用。所有 Git 版本管理和查询只允许在本地完成，部署通过 SSH 配合 rsync/SCP 上传。

底层仍保留未配置 manifest 的本地开发 Git 检查路径，供本地使用；这不授权服务器使用它。服务器 launcher 与执行冻结必须显式配置清单及 SHA，已配置清单的任何缺失、损坏或不匹配均失败退出，不回退 Git。此改动没有改变角色协议、采样、State 递推、Selector 算法、任务、评分或训练额度。

## 完整 engine 清单与服务器证据

清单覆盖 engine 根目录内所有普通文件，包括根模块、原生编译库和裸 `.pyc` / `.pyo`。固定排除的目录仅为 `.git`、`.venv`、`__pycache__`；因此它证明约定范围的内容身份，不声称对整个 Python 环境或运行缓存做了逐文件散列。清单范围内的符号链接和特殊文件被拒绝。

| engine 名称 | 文件数 | 文件字节总和 | manifest SHA-256 |
|---|---:|---:|---|
| `vllm-rwkv-67f0c5996c50` | 6,395 | 145,117,170 | `5c906f8c7c40b96f4a78752131e877726e93f08664df282867fabd43aed47bfa` |
| `vllm-rwkv-67f0c5996c50-selector-clean` | 6,386 | 131,275,931 | `7ee8d7f5bccb4ff6bee2d2fd38f96365931c57abffc65e7c70fad0f8c6bcb21b` |

文件数、大小与清单 SHA 来自 [UPLOAD_ONLY_MANIFESTS.json](UPLOAD_ONLY_MANIFESTS.json)，与本地两份完整 manifest 及 [重启后 attestation](UPLOAD_ONLY_ATTESTATION_AFTER_RESTART.json) 一致。engine 名称中的 `selector-clean` 是既有目录名，不是本报告对 Git 状态的判断。

重启后记录显示 Executor `MainPID=1476740`、Selector `MainPID=1476735`，两者均为 active/running；两套 engine 的 validation 都为 `uploaded_source_manifest` 并记录上述完整文件数，`git_executed=false`。这证明记录时的服务状态和约定文件身份。模型部分保存模型 manifest/config SHA 与权重文件 inode、大小、mtime，以及 manifest 声明的权重 SHA；该脚本未重新散列数十 GB 的权重文件，不应把其元数据记录称为本次完整权重重算。

[PUBLIC_CONFIG_UPLOAD_ONLY_READY.json](PUBLIC_CONFIG_UPLOAD_ONLY_READY.json) 的 GET 健康/目录/能力预检显示 RWKV 模型可见且支持当前 native-state，Selector 登记身份匹配，Strong Planner / Stage Checker 模型可见。该记录明确 `benchmark_started=false`、`inference_requests=0`，不证明实际生成正确。四个 Goal 生成角色的语义 temperature 仍为 0.1。

## 回归与指标采集验证

[先失败再通过及 45 项相关回归记录](UPLOADED_ENGINE_IDENTITY_TEST_TOOL_RECORD.json) 保存了原工具调用的命令、chunk id 和返回摘要：实现前 4 failed / 17 errors，初始实现后 21 passed，最终身份/CLI、Selector 服务和持久 State 注入相关回归 45 passed in 1.79s。该证据类型明确为 `conversation_tool_output_record`：当时未单独保存原始 pytest 日志，首个失败输出还被工具截断，因此这里只引用工具返回摘要，不将重建记录冒称原始完整日志。

[UPLOAD_ONLY_FULL_TESTS.log](UPLOAD_ONLY_FULL_TESTS.log) 记录完整 `tests/` **697 passed in 55.37s**，没有跳过项。上传身份的普通测试见 [test_uploaded_engine_source_identity.py](../../../tests/test_uploaded_engine_source_identity.py)：

- 不调用 Git 即可建立上传身份；依赖 import probe 仍须执行，build profile 仍须存在。
- 内容变更、增删文件、根目录同名模块遮蔽、裸字节码、符号链接被拒绝；错误 manifest SHA、schema、revision、根路径及 source_root 被拒绝。
- 绝对路径、`..`、反斜线等非规范路径及不完整参数被拒绝；固定排除目录不改变源码身份。
- Selector CLI 透传两个身份参数；本地无清单时仍检查 Git revision 和 dirty 状态。测试通过 monkeypatch 对上传路径的 Git 调用直接报错，覆盖了“不能偷偷查询 Git”的边界。

这些边界保证上传身份修改没有以放宽内容校验来绕过约束；完整回归覆盖既有 Torch / State 注入、生产协议及其他普通测试。测试通过属于代码与部署证据，不属于 Agent 增益。

R2 collector 的最终证据为 [33 项指标 fixture 自验](METRIC_COLLECTOR_R2_VERIFICATION/FINAL/SELFTEST/SELFTEST_RESULT.json) 和 [9 项 R2 绑定验证](METRIC_COLLECTOR_R2_VERIFICATION/FINAL/VERIFICATION.json)，均为 passed。collector SHA 为 `77491c782a9482de0be4ce419c250915667411345dff4be357d3829cad5eb02c`。33 项包括 mutation 去重和完整小写 digest、目标拒绝精确前缀、缺失值保留 unknown、100,000,000 bytes 边界、预算/中途 slice 事件、角色调用下界及只读采集；9 项证明显式绑定 R2 定义路径/SHA、原 R1 记录不变、算法不变、真实题序一致及禁止读取封存路径的 guard。后者使用禁止读取的测试 guard，并未读取 Holdout。人工 fixture 不是 Agent 结果，也不是 StateTune 数据。

## 下一步及证据身份

本报告落盘时，R2 最终 `FROZEN_EXECUTION_MANIFEST_R2.json` 尚待创建；[PREREGISTRATION_R2.zh-CN.md](PREREGISTRATION_R2.zh-CN.md) 与 [METRIC_DEFINITIONS_R2.json](METRIC_DEFINITIONS_R2.json) 是新的执行登记，[REGISTRATION_PRESERVATION_R2_CHECK.json](REGISTRATION_PRESERVATION_R2_CHECK.json) 的 14 项检查确认 R1 两份登记与原冻结 SHA 一致、10 个 R2 helper 快照一致、collector 绑定及 R2 文件名正确。最终有效身份须由 root 冻结并逐臂核对。保持同 12 题、相同验收与采样/预算，用全新 `_r2` workspace 和 zero State 完整运行 A、B 两遍；不接续无效 A，不只补 B，不先跑 Ladder，也不跑 E2E-90。未经合法权限和轮次确认不训练。

本报告引用的源码、普通测试、部署记录、清单、指标验证和脚本快照的 SHA-256 见 [UPLOAD_ONLY_EVIDENCE_SHA256SUMS.txt](UPLOAD_ONLY_EVIDENCE_SHA256SUMS.txt)。清单是报告时点的内容快照，后续 R2 最终冻结文件才是执行绑定；旧记录不被本报告覆盖。
