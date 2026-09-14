# 前端演示与调用方式（2026-09-14）

产品目标是 RWKV 自己的 Code Agent / Harness。今天的实例限定为可核对的文件阅读和指定测试，不代表通用项目自动交付能力。

## 使用方式

当前工作机在 WSL 启动服务后，Windows 浏览器访问 **http://localhost:8766**；WSL 内可访问 **http://127.0.0.1:8766**。

```bash
cd /home/chase/GitHub/RWKV-LH
.venv/bin/python scripts/run_web_ui.py --port 8766 --data-root data/frontend_runs
```

运行身份读取已有 `.env.local` 的 Executor 配置。当前连接为 `http://127.0.0.1:29613/v1`，模型 `rwkv7-g1j-13.3b-zero-state-capability-ctx16384`；前端新任务使用 native_required、zero State、精确 token 记录。服务详情按钮显示连接状态。若 SSH 转发在重启后消失，需在 WSL 恢复部署连接；页面不会伪造就绪状态。

1. 点击一个演示按钮。它只填入用户任务和原始文件，不填答案或指定工具顺序。
2. 检查“工具权限”、调用上限、时间上限和已有文件，点击“开始执行”。可自行添加文本/代码文件并修改任务。
3. 总览显示原始回答和终止原因；“RWKV 执行”显示真实参数与工具结果；“完整审计”提供模型输入、输出及因果事件。
4. 点击“下载审计包”保存文件、trace、State 数据库一致性快照与结果。左侧历史记录可随时重新打开。

`submitted` 表示提交了回答，**不是验收通过**；`interrupted` 表示预算或其他边界停止。前端默认显示“未进行外部验收”。无回答会明确显示，不强制模型写总结。

## 两个固定实例

| 实例 | 操作与期望 | 权限与预算 |
| --- | --- | --- |
| 阅读健康检查脚本 | 读取 `verify_public.py`，说明 HTTP `/health`、200 与 `ok=true` 的检查，以及不证明事务行为的限制。没有真实执行，不能声称测试已运行。 | files；6 次 / 300 秒 |
| 运行递归扫描测试 | 运行现有 `check_recursive.py`，依据实际 stdout JSON 与退出码说明结果；验证递归路径及字段/内容保留。不能扩大为整个索引项目全部合格。 | inspect；6 次 / 240 秒 |

原文件复用已获准实验；文件来源登记在 `rwkv_lh/goal_web_assets/demo_tasks.json`。文件会复制到每次独立工作区，评分要点不进入模型输入。指定测试历史两次任务合格证据见 `data/experiments/RWKV_FLIGHT_CAMPAIGN_R1_20260913/focused_test/REPORT.zh-CN.md`。

本轮输入、评分、预算、模型、源码已提前登记于 `data/experiments/RWKV_FRONTEND_DIRECT_R1_20260914/REGISTRATION.json`；新结果以该轮报告为准，失败和采集异常一并保留。

## API（前端使用同一入口）

`GET /api/demos` 返回任务、原始文件和预算。将某个 demo 的 `request`、`seed_files`、`tool_scope`、`max_transitions`、`max_seconds` 交给 `POST /api/runs` 即可启动。新任务默认 `files`，6 次调用、300 秒；工具范围可选 `files` / `inspect` / `coding`。

`GET /api/runs/<id>` 查看状态和原始结果；`/trace` 查看模型事件；`/events` 查看因果事件；`/files` 查看工作区；`/export` 下载证据。调用仍由 RWKV 选择，不根据 demo ID 或路径特判。

`coding` 修改单独复制的 `delivery/workspace`，前端文件页和导出展示该副本；不会写回输入文件。前端暂不自动续跑、接管、推送或训练。需要新任务时明确重新提交，旧任务和 State 证据保留。

## 本轮已核对成功记录

2026-09-14，真实浏览器串行两遍：**4/4任务合格**，零非法参数、零虚称执行、零无回答终止；每项均自主调用一次工具再提交回答。只证明这两个固定实例内通过。

- 阅读脚本：`UI-20260913-235300-075260`、`UI-20260913-235451-604a9e`。
- 运行测试：`UI-20260913-235356-88c5a5`、`UI-20260913-235550-123f72`。

Run ID使用UTC日期，页面时间按本地时区显示。左侧最新两条是第二遍实例，可直接打开演示；点击演示按钮则重新真实运行。首批另外四次并发记录单列，不合并为串行门或性能收益。完整核对见 `EXTERNAL_REVIEW.json`、`MECHANICAL.json`和各次审计ZIP。
