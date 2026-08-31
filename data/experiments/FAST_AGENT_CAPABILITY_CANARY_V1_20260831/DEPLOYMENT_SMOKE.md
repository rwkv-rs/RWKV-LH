# 当前最佳前端部署烟测

验证时间：2026-08-31 07:27–07:40（Asia/Shanghai）

## 定位

本记录只验证当前最佳实验预览的 Web → Product Controller → 2.9B Selector → 13.3B
Executor → Harness 连接是否真实闭合，不是 Agent 能力发布实验，也不覆盖同目录三题 canary 的
completed/external/strict `0/3` 结论。

数据源为本地 Web UI `manual-v1` 请求，目的为隔离部署连通性检查；请求、版本、用途、运行状态、
模型 trace 与 SQLite 事件链均保存在 `data/manual_runs/runs/<RUN_ID>/`。

## 首次失败与根因

首次运行 `UI-20260830-232711-9d7d79` 在任何模型调用前 fail-closed：

```text
ValueError: independent tool Selector requires progressive disclosure
```

失败记录和 worker traceback 原样保留，没有删除或改写。根因不是 2.9B/13.3B 模型输出：Web 的
`/api/runtime/topology` 读取 Supervisor 配置时，通用 env loader 把 `.env` 的非 Supervisor 变量
也注入长生命周期 Web 进程，其中旧 `RWKV_TOOL_DISCLOSURE_MODE=full` 随后被子 worker 继承，
破坏了独立 Selector 所需的 `progressive` 不变量。

系统性修复：

- `load_local_env` 增加显式组件前缀过滤；不指定前缀时仍保留产品 `.env.local` 完整加载语义。
- `SupervisorAPISettings.from_env` 与 `supervisor_policy_from_env` 只允许加载
  `SUPERVISOR_*`，不再污染 `RWKV_*` 或检索凭据命名空间。
- 产品 `.env.local` 显式锁定 `RWKV_TOOL_DISCLOSURE_MODE=progressive`。
- 新增回归同时调用 Supervisor settings/policy，并断言伪造的
  `RWKV_TOOL_DISCLOSURE_MODE=full` 没有进入进程环境。

## 修复后真实运行

运行 `UI-20260830-233140-0dadf4` 成功完成：

- action session 记录 `tool_disclosure_mode=progressive`。
- 2.9B S60/zero 产生 2 次 handoff，依次选择 `calculator`、`final_answer`；两次均严格等于
  eligible labels 上的原始 logit argmax，`generated_text=false`、`postprocessed=false`。
- 13.3B G3 产生 2 次原始输出；外层/嵌套 raw text、UTF-8 byte 数和 SHA-256 全部一致，
  `postprocessed=false`。
- Harness 登记 1 次 `calculator`，状态 `succeeded`；最终文本为 `4`。
- `final_output_matches_persisted_rwkv=true`、`controller_rewritten=false`，输出来源为
  `rwkv_explicit_final_answer_text`。
- worker 从启动到结束约 2.9 秒；没有启动或调用 0.4B Shadow。

只读验证脚本：
`temp/validate_web_smoke_ui_20260830_233140.py`。

## 文件身份

- request SHA-256：`11ea6bd7ddd5548ffdcfeca08bb0d2b11ac7eb61c3e4d7feeac2a7a37f9e5974`
- result SHA-256：`0aead32bee3897e334fd4ba345b47ae1369c1d3511bb61dd2f9e2aa05778e9f7`
- model trace SHA-256：`a37a219dbce815c847b7ce0a5aa18986e5c4b3adf86e30a5f38ee7ecad1a21ef`
- validator SHA-256：`c72e357c2224763cba9163f6fda16b8ebaf1a442af2356814fd9d624fd2f9a8e`

## 回归与部署状态

- 命名空间/stack/Web 定向回归：`18 passed`。
- 完整回归：`706 passed, 1 warning`；唯一 warning 为既有 Python 3.13 多线程进程内
  `fork()` 弃用提示。
- `git diff --check` 通过。
- Web `127.0.0.1:8766`（Goal Studio）、2.9B Selector `127.0.0.1:29621`、13.3B Executor
  `127.0.0.1:29613` 均健康；`29620` 不监听。
- stack 进程/健康拓扑中没有 Router 项；外部 18075 和旧 18070 均不由本地 manager 停止。

端口纠正后，Goal Studio 真实运行 `UI-20260830-235616-e349c4` 在约 2 秒内完成
`calculator → final_answer`，Harness 返回 `7`，且
`final_output_matches_persisted_rwkv=true`。旧 Local Lab 8765 已停止。
