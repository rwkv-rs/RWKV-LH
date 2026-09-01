# RWKV-LH 当前运行栈

更新时间：2026-09-01（Asia/Shanghai）

## 产品拓扑

```text
Strong model endpoint
  ├─ Planner structured call
  └─ read-only Stage Checker structured call

2.9B RWKV Selector service
  └─ one eligible raw-argmax operation

13.3B RWKV service
  ├─ persistent Executor session/State
  └─ clean Auditor sessions/States（默认复用权重，不复用 State）

Controller + Harness + SQLite Causal Ledger + workspace
```

旧 Contract Graph Reviewer、Atom worker pool、0.4B State Router 和 Top-K Executor 复选不属于当前产品拓扑。

## `.env.local` 角色配置

```dotenv
RWKV_LH_PLANNER_BASE_URL=https://planner.example/v1
RWKV_LH_PLANNER_MODEL=strong-model

RWKV_LH_SELECTOR_BASE_URL=http://127.0.0.1:29621
RWKV_LH_SELECTOR_MODEL=rwkv7-g1j-2.9b
RWKV_LH_SELECTOR_MODEL_SHA256=...
RWKV_LH_SELECTOR_HEAD_SHA256=...
RWKV_LH_SELECTOR_INPUT_PROTOCOL=rwkv-lh.exact-tool-selector-input.v8-frontier-only

RWKV_LH_EXECUTOR_BASE_URL=http://127.0.0.1:29613/v1
RWKV_LH_EXECUTOR_MODEL=rwkv7-g1j-13.3b
RWKV_LH_EXECUTOR_MODEL_SHA256=...
RWKV_LH_EXECUTOR_STATE_TRANSPORT=native_required

# 不配置 Auditor override 时复用 Executor 部署，但创建独立 session/clean State。
# RWKV_LH_AUDITOR_BASE_URL=http://127.0.0.1:29614/v1
# RWKV_LH_AUDITOR_MODEL=another-rwkv-model
```

模型名、代际和端口只是配置。生产装配不得依赖固定 G1I/G1J 名称。

## 健康和身份

普通 `/v1/models` 可达不等于 Goal 可运行。`native_required` 还必须验证：

- recurrent state protocol 与客户端精确一致；
- create/append/generate/commit/rollback/import capability 完整；
- parent state、model/profile/build 和 cache binding 回显一致；
- WKV/cache 标记 `authoritative=false`；
- Selector model/head/input protocol/profile portable identity 精确匹配。

identity 或 capability 失配时 fail closed，不静默回退 prompt replay，也不跨模型复用 Selector Head 或 State profile。

## 本轮 G1J 临时测试服务

服务器 `rwkv-8222` 本轮只允许本任务使用 GPU 0 和 3：

| GPU | 临时端口 | 模型 | 用途 |
|---:|---:|---|---|
| 0 | `18230` | G1J 13.3B | Executor/Auditor zero-State 对照 |
| 3 | `18232` | G1J 2.9B | Selector 权重与后续 v8 Head 适配 |

GPU 1/2 是用户的其他实验，不得探测、停止或复用其服务。7.2B 对照已经完成并停止；当前结果不支持为 Auditor 额外常驻 7.2B。

最终交接复核时 `18230/18232` 均未监听，GPU 0/3 无本任务计算进程。GPU 2 上约
17.9 GiB 的 VLLM 进程属于用户实验，未操作。后续继续测试时应在 GPU 0/3 重新启动并复核
模型 SHA、`/v1/models` 和 native-state capability，不能把上表端口当作仍存活的事实。

这些端口不是产品默认值。每次实验都必须记录实际 `/v1/models`、权重 SHA、Head SHA、输入协议、State identity、GPU UUID 和原始结果。

## 启动和状态

```bash
uv run rwkv-lh-stack up --web --worker
uv run rwkv-lh-stack status
uv run rwkv-lh-stack down
```

`down` 只能停止 manager 记录且 PID、start ticks、process group 和 command digest 全部匹配的本项目进程；外部模型服务、用户已有进程和 GPU 1/2 上的实验不属于该命令的删除范围。

## 恢复语义

- 模型服务暂不可用：记录 resumable failure，Goal 保持可恢复；
- WKV cache 丢失：从 Goal/CausalEvent/Action 权威投影重建；
- Selector handoff identity 失配：discard 后重选；
- Audit 或 Stage repair 的 Planner 调用失败：durable feedback 保留，恢复后先提交关联 patch；
- 只有显式 13.3B `final_answer` 且 final RWKV Audit 通过才能完成 Goal。

## 当前并发限制

推理服务本身可高并发不等于 Controller 已实现安全阶段并发。当前产品只有一条 Executor lane 和一个未决 Audit boundary，阶段内仍顺序运行。并发版本必须使用每步隔离 State、独立 Audit boundary，并只合并 Harness/Evidence 事实；不得在线程间共享可变 `RunState` 或合并 WKV。
