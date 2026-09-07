# 服务器运行链清理与当前零态服务记录

轮次：SERVER_RUNTIME_CLEANUP_R1_20260907。服务器：owner 确认的 `rwkv-8222`。状态核查时间：2026-09-07 03:24:59 UTC（北京时间 11:24:59）。

Agent 级：本轮没有执行模型生成、State bootstrap 或 Agent benchmark，因而没有新的 Strict / completed / mutation 数 / 终止原因成绩。角色级没有训练、评测或 State 增益结论。服务启动时加载基座模型与 GET 健康检查不等同生成或验收通过。

## 已完成的停止与删除

用户授权清理旧实验额外产物后，先按项目路径、启动身份和进程组识别，再优雅停止本项目的 6 个旧服务根进程，涉及 14 个登记成员。SERVICE_STOP_RESULT.json 记录旧 systemd 服务停止返回码 0、其余五组 TERM 信号，以及最终 `survivors=[]`、`status=stopped`。没有按 GPU 编号或通用 Python 名称批量杀进程。

| 旧根 PID | 旧监听端口 | 停止方式 |
| ---: | ---: | --- |
| 302301 | 18234 | 停止 rwkv-lh-g1j-zero-public-canary-executor-gpu0-20260902.service |
| 922391 | 18239 | TERM 项目进程组 922378 |
| 993232 | 18238 | TERM 项目进程组 993231 |
| 1222307 | 18240 | TERM 项目进程组 1222306 |
| 1222472 | 18241 | TERM 项目进程组 1222471 |
| 1251779 | 18242 | TERM 项目进程组 1251752 |

随后按 DELETION_MANIFEST.json 中的 371 个明确路径目标直接删除，共登记 **13,193 个文件、72,422,500,606 字节（约 72.4 GB，十进制）**。不建立 retired/archive 副本。逐文件清单保存路径、大小、时间/文件身份与 SHA-256，状态为 deleted。登记的是删除对象的普通文件字节总数；共享文件系统同期可用空间增加 72,529,612,800 字节，受并发写入影响，不能把此差值当作更精确的删除量。

删除范围包括：

- 项目内已退役的角色/工具训练数据、旧实验结果、分析/测试缓存与旧临时启动驱动。
- `data/models/engineering_invalid` 无效模型副本（26,541,906,988 字节），旧 selector_heads 目录，以及旧 runtime 日志、Selector State 缓存和空旧注册目录。
- `/home/chase/chase/RWKV-LH-statetune-v2`、`-v3`、`-v4` 三个旧源码/实验工作副本。
- `RWKV-PEFT/out/` 下清单列出的 8 个相关训练输出目录中的 **runtime 子目录**，包括三份各约 2.08 GB 的运行时 native State 缓存；没有把其父目录的训练 checkpoint 当作运行缓存删除。

完整范围以清单为准，不能据此声称服务器上的全部历史训练成果或其他项目都已清空。远端原项目目录没有 `.git`；本轮没有为未跟踪旧文件制造 Git/GitHub 历史。删除前的路径/SHA 清单用于复核，不含被删除内容的归档副本。

## 保留对象及边界

- 保留 G1J 2.9B / 13.3B 基座模型和必要 tokenizer/config，路径在 `/home/chase/GitHub/RWKV-LH/data/models/`，用于当前零态推理，未重新训练或替换为无效副本。
- 保留 `vllm-rwkv-67f0c5996c50` main 引擎、`-selector-clean` 引擎及现有编译环境 `.venv`。两者 Git HEAD 均为 `67f0c5996c50dca0ad779da545cb491527de988f`；main 包含已存在的 native-state 补丁，Selector clean 树保持干净。没有在引擎环境执行项目依赖同步或降级 Torch。
- 保留 `RWKV-PEFT/out/` 中已训练的 State/checkpoint 与训练元数据供 owner 核对实际累计轮次。它们尚不是当前协议下验证通过的可用成果，也未被新零态服务加载；本次授权清除运行废料不被扩大解释为销毁待对账训练成果。
- 保留其他项目的进程、数据和模型，尤其 GPU2 上的其他项目进程。保留封存题集及 acceptance 边界；本轮不读取、改写或执行 Holdout / confirmation。

## 当前源码与新零态服务

以本地 `cf3a8337` 对应的当前纯 Python 源码镜像更新服务器项目，清除了该镜像范围内的旧源文件/字节码；不是向 main/clean 引擎目录覆盖源码。旧服务已停止后，新建了放在 `data/runtime/launchers/` 的两个独立 launcher，生产不依赖 `temp/` 驱动。Selector decoder manifest 放在 `data/runtime/selector/current_decoder_manifest.json`，由当前协议常量构造并经生产 loader 校验，没有新建角色训练数据目录。

2026-09-07 03:24:59 UTC 的只读 SSH 核查确认：

| 当前 unit | 状态 | MainPID | 地址 | GPU |
| --- | --- | ---: | --- | ---: |
| rwkv-lh-current-zero-executor-20260907.service | active / running | 1465874 | 127.0.0.1:18234 | 0 |
| rwkv-lh-current-zero-selector-20260907.service | active / running | 1465876 | 127.0.0.1:18239 | 1 |

本地 WSL SSH tunnel PID 1269095 监听 `127.0.0.1:29613` 与 `127.0.0.1:29621`。映射分别连接远端 18234 的 Executor API 与 18239 的 Selector 服务；端口号复用不代表复用了旧 PID 或旧服务。

两个 launcher 都明确去掉 State profile manifest；Executor 使用 main 引擎原有 native-state endpoint plugin，Selector 使用 clean 引擎并指定 `profile_id=zero`、profile SHA 与 manifest SHA 全零。四个生成角色在预检配置中也分别显式绑定 zero / 全零 SHA / request delivery，Executor profile routing 禁用。Finalizer 和 Auditor 没有隐式继承训练 State。

相邻基线轮次的 `PUBLIC_CONFIG_READY.json` 在 03:15:19 UTC 记录 GET 预检：RWKV 模型目录可用且配置模型存在；native cache capability 声明完整 `rwkv-lh.native-state.v1`；Selector /healthz 全部 9 个 identity 字段匹配；Strong Planner / Stage Checker 的模型目录检查可用。该文件明确记载 `inference_requests=0`、`benchmark_started=false`，配置状态仍是 `DRAFT_REQUIRES_FREEZE_REVIEW`。此前不可用/旧协议检查记录被保留作为整改前证据，不覆盖为通过。

GET 检查不证明生成质量或零态张量实际行为。初次 import/factory 记录显示 main live `model_states/rwkv.py` 与旧模型 manifest 中的历史 native-state source 登记不同，后续实验须记录实际运行源码 SHA，不能沿用旧登记。

## 模型 identity 与现存文件核验

2026-09-07 03:29:14 UTC 完成补充只读核验：实际模型登记文件名是各模型目录的 `manifest.json`。13.3B 客户端 identity 沿用原始 PTH 的 `source.sha256`；Selector identity 使用转换后 `output.weights_sha256`。二者字段来源不同，不应直接比较后判定权重不一致。本次未修改 launcher、客户端身份或模型 manifest。

| 模型 | 原始 PTH 来源 SHA（manifest 登记） | 现存 model.safetensors SHA（本次 sha256sum） | 客户端 identity 采用 |
| --- | --- | --- | --- |
| G1J 13.3B | 559371f5b9aef13189ae54b345ac096af4ad2b689996c05d89de687612b3ae65 | a5b4fbab12ce321f57ba0e9a00ddf32e5b3644f8b50216cc6ef14aba841efefd | 原始 PTH 来源 SHA |
| G1J 2.9B Selector | 966f3420f833532aae3fb1fd6326533b08d43d23b7b03eaa2f0694a30b64a239 | c1a316e75abd50f5edc3358fbb2c7d1cb18c611d9b2aa5b888091c8d45cc866c | 转换后 safetensors SHA |

两份现存 safetensors 的独立 SHA 计算均与对应 manifest 输出字段一致：13.3B 使用 `output.files["model.safetensors"].sha256`；2.9B 使用 `output.weights_sha256`。原始 PTH 路径只作为 manifest 来源记录读取，未检查其当前存在性、未重新计算其 SHA，也未加载任何权重/State 张量；因此不能把现存 safetensors 核验描述为原始 PTH 现存证明或模型生成能力验证。

本次读取的 13.3B `manifest.json` SHA 为 `4eff9f7054e52d702c43132855e943a8fce3269e578a0160752363775b3d6647`；2.9B `manifest.json` SHA 为 `0d7ae1ce5d32c296ae466ddf023f4482fdc77ba9fcbcd76773c7abc939821c87`。转换是否保持语义的历史登记与当前生成行为是不同证据层，本轮未重新执行转换或其数值等价实验。

## 核验到的部署文件 SHA-256

下表路径均相对于服务器 `/home/chase/GitHub/RWKV-LH/`；本表记录源码和部署工件，现存模型文件的只读 SHA 核验见上一节。未读取训练 State 内容。

| 文件 | SHA-256 |
| --- | --- |
| rwkv_lh/goal_state_protocols/selector_intent_v4.py | c94459290c44329f23bb74502b325bf9bceeb6cb4d831af6e75598cd3de1c10f |
| rwkv_lh/goal_state_protocols/executor_args_v4.py | 4aec4e16bf839ea87e4be95b628e6a077300aab7f3db72bd5736e4b8fa3bc5ed |
| rwkv_lh/goal_state_protocols/auditor_step_v3.py | f718535e650da402cebba04274c2658c04f8f0df072d45a50bbd94500a73c2e9 |
| rwkv_lh/goal_state_protocols/finalizer_answer.py | d42a6c3e9bcec48210caaab52dfdb18fc4d976bae2a57ee0cd177ce21f8671de |
| rwkv_lh/goal_state_protocols/auditor_final.py | bd475596f15ab3187a5653e703cffedb9a5f1d05953f3fd933422f255b3d4b48 |
| rwkv_lh/exact_tool_selector/native_network_service.py | 5970e648ac6086d38b17974472ccab79d57ffa9b7b284cb7978d3120d72e5114 |
| scripts/run_rwkv_e2e_benchmark.py | 7f56fc1c50c415fd9e6f4572e25d40d777ea06e5ec29f8610c40b71f12263ee6 |
| rwkv_lh/benchmark_verifier.py | 005bfb6332b8a7acb86bb7d3283754ea21ff115399ea202878635af9e9450ecb |
| data/runtime/launchers/executor_current_zero.sh | 810182f3cce9f18a9b55ad928126c7a08bb88dfa7b108a302073c7e7c733cf21 |
| data/runtime/launchers/selector_current_zero.sh | 3973a23bfaa87457fbbb6d79d3e5a59305aa07397e603b698b8c54cb5b372eff |
| data/runtime/selector/current_decoder_manifest.json | 9049329c79e89f057e2631bdba7cae771074e025c1df8b23bd4494e4f36f776b |

## 剩余工作与使用限制

服务器清理、当前协议源码第一次同步、两项零态服务启动和 GET 连通检查已完成。新真实项目开发题集及其通用黑盒验收代码正在本地整合，**尚未二次 rsync 到服务器**。例如本次核验时本地 `benchmark_verifier.py` 为 `4c2c231df30d2b917ae4c391ba43f79e1f0c8987136f213fcdec855077e3d0a6`，服务器仍是上表旧版；不能把当前服务就绪描述为新 benchmark 已完成部署或已开始全面测试。

下一步须完成真实项目任务与验收整合、参考/错误候选隔离验证、全量代码回归与题集冻结，再同步最终代码并固定所有源码/模型/协议/参数身份，才进入新题集 zero-state 基线。两臂之间改动 rwkv_lh/ 必须按规范重跑两臂。训练及最终 Holdout 均未在本轮启动；角色训练额度仍须按 AGENTS 完成 owner 对账。

## 证据索引

- `PROJECT_PROCESSES_BEFORE.json`、`SERVICE_STOP_RESULT.json`：停止前身份与停止结果；停止结果 SHA `8c778657d7ad66939e2f915620000722369c875313c4bff561ed3e7f4e3eed53`。
- `SERVER_DIRECTORY_INVENTORY.json`、`SERVER_ADDITIONAL_DIRECTORY_INVENTORY.json`、`OLDER_WORKTREE_INVENTORY.json`、`REMOTE_SOURCE_BEFORE.sha256`：删除/同步前路径与来源登记。
- `DELETION_MANIFEST.json`：完整删除清单与最终状态；SHA `1345d8207c5845eb405e09900155456b1d438cd28a67fecbd74743717eabf191`。`deletion_registration.log` 保留删除前登记过程。
- `CURRENT_DEPLOYMENT_ARTIFACTS.json`：新 launcher 与 decoder manifest 的内容/SHA；SHA `4fa031b59f975a24895b3923f4806aefd46da854cf8ad8957670de22537a2562`。
- `../ZERO_STATE_AGENT_BASELINE_R1_20260907/PUBLIC_CONFIG_READY.json`：无生成 GET 预检；SHA `73c7880a587ac69860c84c4c6c4c78574e05f4f222ff5b0a32498e068a7146c4`。
- `../ZERO_STATE_AGENT_BASELINE_R1_20260907/REMOTE_CURRENT_SOURCE_IMPORT_AUDIT.json` 与 `REMOTE_NATIVE_PLUGIN_FACTORY_CHECK.log`：更新后源码导入、现有 native endpoint 工厂可用性及 live engine source SHA；均未执行模型生成。
- 本目录 `SHA256SUMS` 覆盖本报告与本目录全部证据文件，排除清单自身；可在本目录执行 `sha256sum -c SHA256SUMS` 复核。
