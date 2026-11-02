# RWKV-LH

单一模型 RWKV 编码 Agent 与其 Harness。一个 RWKV 模型以一个持续 State 处理用户请求：自主选工具、读取文件、实现、自测、修复，并以 `finish_work` 声明结束当前请求；用户的后续请求在同一会话、同一 State、同一工作区中继续。推理时没有第二个模型，没有 Planner 或工单。当前 RWKV 没有视觉能力，浏览器操作、截图和视觉检查由独立验收器在执行链外完成。模型声明、执行事实和外部检查结果分别记录。职责、协议与执行边界见[当前架构](docs/ARCHITECTURE.zh-CN.md)。

Agent 使用固定九工具：`Read`、`Write`、`Edit`、`Bash`、`ListDir`、`Grep`、`BashOutput`、`KillShell`、`finish_work`。模型输出为 `<think>` 推理、可选叙述和一个或多个 Qwen3-Coder 标签调用，并以 EOS 结束一轮；一轮可提交多个调用，整批验证后按顺序执行，调用与回执通过 call ID 对应。

训练数据由离线数据引擎产生：先生成任务，RWKV 实际执行，Qwen 只作为离线教师纠正 RWKV 的错误轮，最后只采纳经真实执行和隐藏检查验证的样本。项目仍处于实验阶段；工程回归通过不能代替 Agent 能力验收。

## 安装与配置

维护和验证环境为 WSL UbuntuRecovered，Harness 使用 Python 3.10 及以上，独立训练/推理环境使用 Python 3.12 及以上。安装完整依赖：

```bash
uv sync --frozen --extra selector-runtime --extra benchmark-web --group dev
.venv/bin/python -m playwright install chromium
```

首次配置参照 [.env.example](.env.example) 创建 `.env.local`，只需提供 RWKV 推理服务。RWKV 端点读取 `RWKV_LH_PROJECT_EXECUTOR_*`（回退 `RWKV_LH_EXECUTOR_*`；名称沿用旧前缀，作为稳定的部署配置）。未设置初始 State 时从 zero 开始；同一会话内的后续请求不重置 State；进程环境变量优先于配置文件。旧 `RWKV_LH_PLANNER_*` 配置已不再读取，可删除。

配置后用 `rwkv-lh-stack status` 核对服务，用 `rwkv-lh-runtime-smoke` 检查运行链路。以下命令均位于 `.venv/bin/`，也可在激活虚拟环境后直接使用。

## 后端

训练统一使用 **skyrl-rwkv**，推理统一使用 **irwkv**。版本固定在 `rwkv_lh/skyrl.lock.json` 和 `rwkv_lh/inference/irwkv.lock.json`。引擎使用各自隔离环境；Harness 环境不安装 GPU 服务。后端环境安装本项目时使用 `uv pip install --no-deps -e /absolute/path/to/RWKV-LH`，由对应引擎管理 Torch、Transformers 与 FlashRWKV2 的固定版本。

实际模型转换在安装了固定 Transformers-RWKV 的 irwkv 环境中运行；训练和推理登记中的 `python` 分别指向各自引擎环境的解释器。`--help`、准备与配置核验可在 Harness 环境运行。

模型使用标准 Transformers-RWKV safetensors 格式。`rwkv-lh-artifact --help` 查看固定转换器及 SHA 参数，`rwkv-lh-train --help` 查看训练交接，`rwkv-lh-seal-export --help` 查看训练导出封装，`rwkv-lh-serve --help` 查看推理部署。训练和服务入口都需要冻结 JSON 登记及 SHA，默认只准备，显式 `--execute` 才启动；训练 reader 只接受经 owner 封存和审计的当前 `transcript_tokens`，完整 token 与监督 mask 不截断，不转换或重标旧数据；登记字段和 State 身份规则见[架构说明](docs/ARCHITECTURE.zh-CN.md)。

训练通过 SkyRL 原生 SFT（全参数 `sft_full` 或 NoRA `sft_nora`）保留完整 token/监督 mask，并使用原生 checkpoint 恢复；训练采用 BF16 权重/计算，递归 State 的 wkv 为 FP32、两个 token-shift 池为 BF16；推理同样采用 BF16 权重/计算，wkv 为 FP32、两个 token-shift 池为 BF16。服务 profile 为 `irwkv-native`，默认单卡、每个会话一个持续 State。换后端后需要重新验证模型与 State，工程迁移不代表已经重训或证明能力提升。

## 执行任务

```bash
.venv/bin/rwkv-lh \
  --source-workspace /absolute/path/to/project \
  --output-dir /absolute/path/to/new-run \
  --request "检查项目中的问题，修复后运行相关测试并说明结果" \
  --protected-paths ./private \
  --max-calls 64 --max-seconds 600
```

输出目录必须尚不存在，且不能与源目录重叠。Agent 在输出目录的 `workspace/` 副本中修改文件，执行记录位于 `execution/`；逐步命令与反馈见 `execution/PROGRESS.jsonl`，终态见 `DELIVERY.json`。默认可写整个工作区，`--writable-paths` 可限定可写路径（可重复），`--protected-paths` 指定只读路径；权限在会话创建时固定。

后续请求在同一会话中继续（同一 State、同一工作区、同一账本），预算只增不减：

```bash
.venv/bin/rwkv-lh --continue /absolute/path/to/new-run \
  --request "再为新增函数补充单元测试" --extra-calls 32 --extra-seconds 600
```

只有当前请求已结束（`finished`、`blocked` 或 `interrupted`）且没有未确认操作时才接受后续请求。进程异常或 `checkpoint_yield` 后，用 `rwkv-lh --resume /absolute/path/to/new-run` 在服务仍保有 State 时恢复当前请求；未知操作不会自动重放。

工作区保留指向项目内部有效目标的相对符号链接，支持 npm 命令入口和项目内本地包随安装、构建及快照连续使用。绝对链接、越界、悬空或循环链接会报告具体错误；链接不能扩大写入权限。`Bash` 使用共享宿主网络下载依赖、访问服务，文件仍在隔离工作区中执行。它支持普通 HTTP/HTTPS 代理地址和 WSL DNS，npm 缓存放在命令临时目录，宿主凭据与用户 npm 配置不会自动继承。`Bash` 的后台模式返回作业 handle，后续用 `BashOutput` 读取增量日志、`KillShell` 停止；后台作业留在独立沙箱和私有工作区中，活跃期间不发布异步写入。确认停止后才核对并提交授权范围内的变更，运行结束时回收作业。日志出现 ready 只代表输出事实，不能保证服务仍然存活。

`finish_work` 结束当前请求；退出码 0 表示 `termination=agent_finished`。`finished` 与 `blocked` 都是模型声明，当前始终 `completed=false`、`acceptance=not_evaluated`，**不代表通过验收**。预算耗尽、输出截断和连续协议拒绝都按中断处理；模型仍可能重复调用、遗漏修改或无依据声明完成。

不带参数启动 `rwkv-lh` 进入交互终端：第一句需求新建会话，之后每句需求都作为同一会话的后续请求继续。使用 `--jobs` 批量运行互相独立的会话（JSON 数组，字段同 `CodingJob`：`task_id`、`request`、`workspace`、`output_dir`、预算、`writable_paths`、`protected_paths`）。全部参数见 `rwkv-lh --help`。

## 查看网页产物

已有静态网页可直接预览，不调用模型：

```bash
.venv/bin/rwkv-lh --preview /absolute/path/to/workspace --port 8767
```

外部预览可用 `--launch /absolute/path/to/workspace --launch-kind npm --launch-script preview`，在隔离副本中安装依赖、运行 `build` 和 `preview`；需要 Node/npm、bubblewrap 与依赖下载网络。项目须声明这些 npm 脚本并构建 `dist/index.html`，不要求特定框架。使用 `--launch-script dev` 时只安装并运行 `dev`，不证明生产构建成功。服务脚本接收 `HOST=127.0.0.1`、`PORT` 及 `--host`/`--port` 参数；当前不覆盖后端、SSR 或自定义输出。终端按 Ctrl+C 停止预览。这些命令不调用模型，浏览器验收结果另行保存。

任务管理 Web 界面使用 `.venv/bin/rwkv-lh-web --port 8766 --data-root data/frontend_runs` 启动。执行任务会调用已配置的真实模型，并保存原始输出、每个请求的声明和工具回执。

## 发布范围与验证

GitHub 保留维护中的源码、通用入口、必要构建配置，以及本 README 和架构说明。交接、经验、方案、实验记录、`AGENTS.md`、测试、基准、根目录 `data/` 和 `temp/` 均仅在本地维护；源码包采用相同文档边界。

公开 CI 检查源码范围、编译、命令入口及 sdist/wheel 构建。完整回归需由 owner 单独交接本地测试及必要夹具后，在上述完整环境运行 `.venv/bin/python -m pytest -q tests/`，不跳过 Torch、State 或必需浏览器验证。CI 通过与完整回归、Agent 验收分别报告。
