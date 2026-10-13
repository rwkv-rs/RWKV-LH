# RWKV-LH

面向前端项目完整交付的 RWKV Harness 与编码 Agent。强 Planner 只生成一次初始计划，RWKV Executor 使用同一个持续 State 创建项目、生成和修改代码、运行命令，并根据实际报错调试、测试、构建和交付。当前 RWKV 没有视觉能力，浏览器操作、截图和视觉检查由 Codex 或独立验收器在执行链之外完成，不分配给 RWKV。模型声明、执行事实和外部检查结果分别记录。职责、协议与执行边界见[当前架构](docs/ARCHITECTURE.zh-CN.md)。

默认工作区工具为 `list_directory`、`search_files`、`read_file`、`write_file`、`replace_text` 和 `run_shell`。命令执行保留权限范围内的文件变更，构建产物可由后续操作读取；模型另可读取已有回执或声明结束。没有 Decision RWKV、在线强模型复核或重新规划调用。

在相同交付质量下降低强模型消耗是优化目标，当前尚未证明成本与完成率收益。项目仍处于实验阶段。

项目级评测须先验证并冻结来源版本、需求、资产、依赖、数据合同与验收规则。Agent 只接收规格与允许开发材料，完整参考实现和私有检查留在工作区外。评测来源与真实生产纠错训练来源按项目族隔离；工程回归通过不能代替项目交付及重复运行验收。

## 安装与配置

维护和验证环境为 WSL UbuntuRecovered，Python 3.10 及以上。安装完整依赖：

```bash
uv sync --frozen --extra selector-runtime --extra benchmark-web --group dev
.venv/bin/python -m playwright install chromium
```

首次配置参照 [.env.example](.env.example) 创建 `.env.local`。需提供 RWKV 推理服务与强模型服务；Executor 读取 `RWKV_LH_PROJECT_EXECUTOR_*`，强 Planner 使用 Supervisor 配置。未设置 Executor State 时从 zero 开始，项目内切换步骤不重置 State；进程环境变量优先于配置文件。

配置后用 `rwkv-lh-stack status` 核对服务，用 `rwkv-lh-runtime-smoke` 检查运行链路。以下命令均位于 `.venv/bin/`，也可在激活虚拟环境后直接使用。

## 执行任务

```bash
.venv/bin/rwkv-lh \
  --source-workspace /absolute/path/to/project \
  --output-dir /absolute/path/to/new-run \
  --request "检查项目中的问题，修复后运行相关测试并说明结果" \
  --max-calls 64 --max-seconds 600
```

输出目录必须尚不存在，且不能与源目录重叠。Agent 在输出目录的 `workspace/` 副本中修改文件，执行记录位于 `execution/`；逐步命令与反馈见 `execution/PROGRESS.jsonl`，终态见 `DELIVERY.json`。工作区副本隔离文件变更，命令仍使用现有工具权限。

工作区保留指向项目内部有效目标的相对符号链接，支持 npm 命令入口和项目内本地包随安装、构建及快照连续使用。绝对链接、越界、悬空或循环链接会报告具体错误；链接不能扩大写入权限。前端 `run_shell` 使用共享宿主网络下载依赖、访问服务，文件仍在隔离工作区中执行。它支持普通 HTTP/HTTPS 代理地址和 WSL DNS，npm 缓存放在命令临时目录，宿主凭据与用户 npm 配置不会自动继承。服务需在命令生命周期内启动、检查及停止，目前没有跨调用持久后台服务保证。

退出码 0 表示 Executor 调用 `finish_work` 正常结束；`finished` 是模型声明，当前始终 `completed=false`、`acceptance=not_evaluated`，**不代表通过验收**。预算耗尽按中断处理；模型仍可能重复调用、遗漏修改或无依据提交。推理服务仍保有本次 State 时，可用 `rwkv-lh --resume /absolute/path/to/new-run` 沿原预算恢复；默认内存 State 在服务重启后失效，未知操作不会自动重放。

不带参数启动 `rwkv-lh` 可进入交互终端，也可直接传入一句需求创建新项目。使用 `--jobs` 批量运行独立任务；全部参数见 `rwkv-lh --help`。

## 查看网页产物

已有静态网页可直接预览，不调用模型：

```bash
.venv/bin/rwkv-lh --preview /absolute/path/to/workspace --port 8767
```

外部预览可用 `--launch /absolute/path/to/workspace --launch-kind npm --launch-script preview`，在隔离副本中安装依赖、运行 `build` 和 `preview`；需要 Node/npm、bubblewrap 与依赖下载网络。项目须声明这些 npm 脚本并构建 `dist/index.html`，不要求特定框架。使用 `--launch-script dev` 时只安装并运行 `dev`，不证明生产构建成功。服务脚本接收 `HOST=127.0.0.1`、`PORT` 及 `--host`/`--port` 参数；当前不覆盖后端、SSR 或自定义输出。终端按 Ctrl+C 停止预览。这些命令不调用模型，浏览器验收结果另行保存。

任务管理 Web 界面使用 `.venv/bin/rwkv-lh-web --port 8766 --data-root data/frontend_runs` 启动。执行任务会调用已配置的真实模型，并保存原始输出和工具回执。

## 发布范围与验证

GitHub 保留维护中的源码、通用入口、必要构建配置，以及本 README 和架构说明。交接、经验、方案、实验记录、`AGENTS.md`、测试、基准、根目录 `data/` 和 `temp/` 均仅在本地维护；源码包采用相同文档边界。

公开 CI 检查源码范围、编译、命令入口及 sdist/wheel 构建。完整回归需由 owner 单独交接本地测试及必要夹具后，在上述完整环境运行 `.venv/bin/python -m pytest -q tests/`，不跳过 Torch、State 或必需浏览器验证。CI 通过与完整回归、Agent 验收分别报告。
