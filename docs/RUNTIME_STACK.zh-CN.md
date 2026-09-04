# RWKV-LH 当前运行栈

更新时间：2026-09-04（Asia/Shanghai）

## 产品拓扑

```text
Strong model endpoint
  ├─ Planner structured call
  └─ read-only Stage Checker structured call

2.9B RWKV Selector service
  └─ one eligible raw-argmax operation

13.3B RWKV service
  ├─ one clean Executor State per selected action
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
RWKV_LH_SELECTOR_INPUT_PROTOCOL=rwkv-lh.g1j-per-stage-state-tuning.selector-intent.v1

RWKV_LH_EXECUTOR_BASE_URL=http://127.0.0.1:29613/v1
RWKV_LH_EXECUTOR_MODEL=rwkv7-g1j-13.3b
RWKV_LH_EXECUTOR_MODEL_SHA256=...
RWKV_LH_EXECUTOR_STATE_TRANSPORT=native_required
RWKV_LH_EXECUTOR_STATE_PROFILE_ID=zero
RWKV_LH_EXECUTOR_STATE_PROFILE_SHA256=0000000000000000000000000000000000000000000000000000000000000000

# 不配置角色 override 时复用 Executor 部署，但每个角色创建独立 session/clean State。
# RWKV_LH_AUDITOR_STEP_MODEL=another-rwkv-model
# RWKV_LH_FINALIZER_MODEL=another-rwkv-model
# RWKV_LH_AUDITOR_FINAL_MODEL=another-rwkv-model
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

## G1J StateTune 服务状态

2026-09-03 的 zero-State Ladder trace 已证明旧 Selector Head 存在训练/运行轨迹不一致：离线特征是共用 bootstrap 的独立样本，在线却延续 parent WKV。该 Head 已从运行时身份中淘汰；新 Head 必须声明 `persistent-causal-sequences.v1` 并由同分布轨迹产生。Executor 也改为每个已选 action 干净启动，避免旧工具和格式锚点污染下一次参数生成。后续每次实验必须重新登记实际 `/v1/models`、权重 SHA、Head SHA、输入协议、State identity、GPU UUID 和原始结果。

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
