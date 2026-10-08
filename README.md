# RWKV-LH

面向 RWKV 状态续写模型的 Harness 与编码 Agent。强 Planner 生成一次初始步骤计划，RWKV Executor 使用同一个持续 State 自主选择步骤、读写文件、运行工具、接收反馈并结束。当前先建立完整可观察的执行轨迹，已删除 Decision、在线审查和重新规划。模型声明完成与实际工具事实分别记录，错误也会原样保留。职责、协议与执行边界见[当前架构](docs/ARCHITECTURE.zh-CN.md)。

在相同交付质量下降低强模型消耗是优化目标，当前尚未证明成本与完成率收益。项目仍处于实验阶段。

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

退出码 0 表示 Executor 调用 `finish_work` 正常结束；`finished` 是模型声明，当前始终 `completed=false`、`acceptance=not_evaluated`，**不代表通过验收**。预算耗尽按中断处理；模型仍可能重复调用、遗漏修改或无依据提交。推理服务仍保有本次 State 时，可用 `rwkv-lh --resume /absolute/path/to/new-run` 沿原预算恢复；默认内存 State 在服务重启后失效，未知操作不会自动重放。

不带参数启动 `rwkv-lh` 可进入交互终端，也可直接传入一句需求创建新项目。使用 `--jobs` 批量运行独立任务；全部参数见 `rwkv-lh --help`。

## 查看网页产物

已有静态网页可直接预览，不调用模型：

```bash
.venv/bin/rwkv-lh --preview /absolute/path/to/workspace --port 8767
```

标准 Vite 项目可用 `--launch /absolute/path/to/workspace --launch-kind vite` 安装、构建并预览，需要 Node/npm、bubblewrap 与依赖下载网络。当前支持根目录 `index.html`、`build` 脚本和 `dist/index.html`，不覆盖后端、SSR 或自定义输出。终端按 Ctrl+C 停止预览；页面能打开仍需另行验证功能。

任务管理 Web 界面使用 `.venv/bin/rwkv-lh-web --port 8766 --data-root data/frontend_runs` 启动。执行任务会调用已配置的真实模型，并保存原始输出和工具回执。

## 发布范围与验证

GitHub 保留维护中的源码、通用入口、必要构建配置，以及本 README 和架构说明。交接、经验、方案、实验记录、`AGENTS.md`、测试、基准、根目录 `data/` 和 `temp/` 均仅在本地维护；源码包采用相同文档边界。

公开 CI 检查源码范围、编译、命令入口及 sdist/wheel 构建。完整回归需由 owner 单独交接本地测试及必要夹具后，在上述完整环境运行 `.venv/bin/python -m pytest -q tests/`，不跳过 Torch、State 或必需浏览器验证。CI 通过与完整回归、Agent 验收分别报告。
