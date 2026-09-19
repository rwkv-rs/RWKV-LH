# TEMP_CLEANUP_R1_20260919

本轮为 owner 授权的本地 temp 清理。Agent Strict / completed / mutation / 终止原因：未运行 Agent，无新指标；角色指标与训练：未运行。

在 WSL UbuntuRecovered 执行。temp 磁盘占用由约 298 MiB 降至 7.9 MiB。删除 18,068 个文件或符号链接，文件内容计 250,456,201 bytes（238.85 MiB）；磁盘占用还包含目录、块分配等开销，二者不等同。

删除范围：三个旧参考源码目录 native_engine_role_chain_r1_20260910、dsh_reference_review_20260912、statetuning_reference_20260914，__pycache__，以及修改时间早于 2026-09-16 的未跟踪 .py/.sh 一次性脚本。两个参考 Git checkout 的 tracked status 干净；未对第三方项目进行源码开发。未保留副本或压缩归档，未跟踪脚本不能从本仓库 Git 恢复。旧实验文档中的历史路径仍按原样保留，相关一次性脚本不再保证可直接重跑。

保留全部 40 个 Git 跟踪 temp 文件、近期工作文件、日志、补丁及其他未明确归类的材料。未修改生产代码、测试、数据集、验收保留集或服务器；原有五处代码/测试工作区修改未纳入本轮提交。

检查：生产 rwkv_lh/、scripts/、tests/、pyproject.toml 搜索未发现对本 temp 的直接引用；进程列表未发现运行中的 temp 脚本。执行后逐项确认删除路径不存在，40 个跟踪文件全部存在。删除清单记录每项路径、类型、字节数、SHA-256 与分类原因，链接摘要基于链接目标文本，不跟随链接读取。

删除清单：deleted_manifest.jsonl，SHA-256 `09909b64d1197ea914861fe4e7d921435751f9835b6930abd265fdea60a728ee`。
执行脚本：temp/cleanup_temp_r1_20260919.py，SHA-256 `b8bf2d669c38ba8259f72a0466daf76438e525fe9ddbac18d81b894ca6f190be`。
统计与保留项：summary.json。

环境：uv sync --frozen --extra selector-runtime --extra benchmark-web --group dev 成功；.venv/bin/python -m playwright install chromium 成功。完整回归 `.venv/bin/python -m pytest -q tests/`：1894 passed in 362.05s，0 skipped，退出码 0。没有运行 acceptance_tests/。
