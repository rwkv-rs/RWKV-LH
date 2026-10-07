# 当前源码发布范围与本地验证

GitHub 只发布维护中的项目源码、架构和操作文档、必要构建配置。测试和实验材料保留本地；该边界同样适用于新分支及其待上传历史。

## 公开源码

保留 `rwkv_lh/` 的运行时、协议、模型适配、训练与数据管线、原生计算源码、词表和 UI 资源；保留 `scripts/` 的通用命令、`docs/`、README、LICENSE、AGENTS、锁文件与构建配置。通用验证器属于实现，具体试题、答案和结果不属于公开源码。

`tests/`、`acceptance_tests/`、`benchmarks/`、根目录 `data/`、`temp/`、`outputs/`、训练 State、日志和生成项目全部留在本地。以下专项脚本也不提交：

- `scripts/freeze_project_benchmark.py`
- `scripts/generate_agent_capability_ladder_v1.py`
- `scripts/generate_agent_v1_project_suite.py`
- `scripts/prepare_project_natural_dev.py`
- `scripts/run_calendar_project_trial.py`
- `scripts/run_rwkv_e2e_benchmark.py`
- `scripts/test_calendar_project.py`
- `scripts/test_project_basics.py`
- `scripts/test_project_expense_tracker.py`

`.gitignore` 使用根目录允许列表，不得用 `git add -f` 绕过。权重、凭据、State 不放进源码目录；`rwkv_lh/data/` 的运行词表不等于根目录实验数据。

## 上传与身份

上传前检查最终树和所有尚未发布的祖先。若本地开发历史包含仅限本地的材料，以已有远端提交作父创建当前源码快照提交，发布到新分支；保留本地研发历史，不 force push，不自动改 main。这样避免新增发布本地实验历史，不能抹除远端已存在的历史对象。记录本地源码提交、发布提交、相同树 SHA 和远端核验结果。

只选择本轮已验证修改提交，现存未提交工作保持原样。完整回归若包含 owner 未提交源码，须明确其冻结清单，不能把它当作纯提交源码的同一测试对象。用户明确授权上传时可直接执行 push；其余按项目工作规范由 owner 推送。

所有 Git 操作仅在本地 WSL。服务器接收 rsync/SCP 上传的冻结源码及逐文件 SHA/manifest SHA，不运行 Git，也不在清单缺失时回退 Git 身份。

## 构建与本地验证

发布构建从干净已提交源码导出或新 clone 运行，防止未提交文件混入包。`MANIFEST.in` 排除本地材料，包发现只含公开 `rwkv_lh` 和 `scripts`，保留必需的 C++/CUDA 源码。

公开 CI 检查源码边界、Python 编译、六个命令的 `--help` 和 sdist/wheel 构建，不依赖本地测试、GPU、凭据或实验数据。它通过不等于完整回归或 Agent 验收通过。

完整回归仅在已接收本地测试和夹具的 WSL UbuntuRecovered 环境执行：

```bash
uv sync --frozen --extra selector-runtime --extra benchmark-web --group dev
.venv/bin/python -m playwright install chromium
.venv/bin/python -m pytest -q tests/
```

Torch、State 注入和必需浏览器验证不得跳过。新 clone 不含私有 tests，由 owner 单独交接必要测试、`data/test_fixtures/` 及开发基准；不交接 `.env.local`、原始权重、推理 State 或受保护 Holdout。缺材料不能标记通过。

本地测试按独立行为和失败模式保留，修复优先扩展已有行为测试。相同校验规则按不同 schema 与边界值覆盖，每个注册字段仍参与 schema 收集，避免工具名与相同规则机械交叉展开。提示词措辞、任意字数、常量自我比较和导入别名不单独构成回归目标；有实际产品合同的字节、版本和身份约束仍须验证。公开构建与六入口帮助检查由 CI 负责，真实 CLI、浏览器、Native、State、恢复及异常行为保留本地回归。删除测试前登记原 SHA、理由及替代覆盖，精简后运行完整回归；用例数减少不等于模型能力或运行性能改善。

逐轮日志、实验原文、SHA 与失败记录保存在本地 `data/experiments/`。维护文档仅保留当前规范，最新验证证据从[当前交接](HANDOFF.zh-CN.md)进入；不在公开文档累积历史轮次。
