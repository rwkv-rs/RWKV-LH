# RWKV Agent 状态链、执行权与 Goal 生命周期整改 V1 结果

结果日期：2026-08-31（Asia/Shanghai）。本文件只记录冻结方案的最终可复核结果，不收录开发期
假设、失败尝试或已推翻结论。

## 1. 结论

代码整改与离线生产链路验收通过；当前 live 13.3B serving 尚未实现所需 native-state capability，
因此线上 Goal readiness 仍为 false。产品链路对此 fail closed 并等待服务恢复，不会退回 prompt
replay。不能把确定性协议 fixture 的通过解释为 live RWKV 原生状态链已经部署。

已建立并验证以下系统不变量：

1. 正常 continuation 使用 `state + current delta`，健康 native lane 不重放完整历史；16K 只约束
   单次 bootstrap/delta，而不是累计任务历史。
2. WKV state 与 Selector state 均标记为 `authoritative=false`、
   `cache_role=disposable_acceleration`；缓存丢失时由 Goal/Action 权威投影重建。
3. 在线 selection 事件为 `exact_tool_selection_staged`。Executor 在当前父状态、模型、profile、
   工具定义和 atom contract 下重新授权并消费；`exact_tool_selection_committed` 只保留历史读取兼容。
4. Goal 模式为 `self_termination_only`。预算、协议、动作和 runtime 故障只会 yield/checkpoint/等待；
   只有显式 RWKV `final_answer` 可以完成 Goal。
5. 读取型 atom 只有在自身声明范围内存在成功、直接且相关的 observation 才允许完成，父目录枚举
   或无关读取不能冒充目标读取。

## 2. 真实项目“母路径”验收

正式验收没有使用微型 mock 工程。测试从当前真实项目内容生成受摘要约束的完整代码快照，并将
该快照目录本身直接设为 `Goal.workspace_root`：

`run_real_project_parent_workspace_v1/workspace`

语义决策使用固定 native-state protocol fixture，只替代模型采样；Controller、Model、
`NativeRWKVModelSession`、Harness、SQLite Store、causal projection 和 bubblewrap 均走生产代码。

- 生产 Harness Action：14 个；模型 Decision：15 个；native-state service 调用：59 次。
- 动作覆盖：目录枚举、代码搜索、缺失读取、越界读取、正常读取、建目录、写入、追加、替换、复制、
  移动、摘要、沙箱命令、删除、RWKV 显式 Final。
- 缺失文件得到 `FileNotFoundError`；`../AGENTS.md` 得到 `ScopeViolation`；两次失败后仍继续完成。
- `generate` 只携带 state ref，不携带历史 prompt；所有 append 都只发送本步 delta。
- WKV cache 全程非权威；在线没有产生 committed selection；只有一次 RWKV Final 完成事件。
- 原项目所选源文件 manifest 在 Agent Action 前后完全一致。
- 预注册 `exact_position_accuracy = 23 / 23 = 1.000000`，达到固定阈值 `1.000000`。

证据：`run_real_project_parent_workspace_v1/SOURCE_MANIFEST.json`、`RUN_PROTOCOL.json`、`RESULT.json`。

## 3. 全路径与历史回归

- 定向链路：`136 passed in 11.07s`，通过率 1.0。
- 全量：`723 passed, 1 warning in 89.60s`，通过率 1.0；唯一 warning 是 Python 3.13
  multiprocessing fork deprecation，不是测试失败。
- Python 全树 `compileall`：通过。
- `git diff --check`：通过。
- 历史三条真实 ledger：3/3 源摘要匹配，25 个 atom outcome 全量扫描。
- 历史 9 个“没有相关直接读取却被标记完成”的结果，按新门禁 9/9 被阻止；新 false completion=0。
- 冻结 S23/S24 数据生成兼容：payload 与 README 均 byte-exact，兼容得分 1.0。

正式回归详情见 `FORMAL_REGRESSION_RESULT.json`、`HISTORICAL_TRACE_AUDIT.json` 和
`FROZEN_DATASET_GENERATOR_COMPATIBILITY.json`。

## 4. Live 部署边界

2026-08-31 对当前主模型服务的只读探测显示：

- `/v1/models` 返回 HTTP 200，模型声明 `max_model_len=16384`；
- `/v1/capabilities` 返回 HTTP 404；
- 所需 `recurrent_state_protocol=rwkv-lh.native-state.v1` 未被 serving 声明；
- `native_goal_ready=false`；Goal 不允许 prompt-replay fallback。

因此本轮代码侧系统性缺陷已修复并通过全部登记验证，但 live 原生状态链上线还需要 serving 层实现
并声明 `/v1/state/create|append|fork|generate|commit|rollback|import` 与 capability 协议。完整客观响应
见 `LIVE_RUNTIME_CAPABILITY_AUDIT.json`。

## 5. 证据摘要

- 预注册 SHA-256：`fce643b1e86a2702d9de1fd211289cc907da6a131fa8c500ca14ab29b534562c`
- 真实项目来源 manifest 文件 SHA-256：
  `504483377c20c83f6fed5c1bacce37753ea562217cd2eeb7aaaa3754bccbf78c`
- 真实项目 run protocol SHA-256：
  `b42fcc388bee8e89338bb2a1da38ebc17b54be17d768b238cb37850ac572c15e`
- 真实项目 result SHA-256：
  `5ba18daae4dafd758288d0bb23a10c9deae9095dca7fafdd324d8758f7837464`
- 历史审计 SHA-256：`e325c526368267e46d397c70f8b1acc32db7acb487411150607453b01d82d3e6`
- 冻结数据兼容审计 SHA-256：
  `24cd7b6671ef71a0d1da17c8e913e1515fd1cf9ce9ad58bf40000541ca061d6f`
- Live capability 审计 SHA-256：
  `077a1e1e167d57e3911b4845a20a4095f6f1f4b6e0f509837c4791617e533fb4`
