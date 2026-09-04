# RWKV-LH 分进程运行栈

当前产品运行栈严格对应已经验证的职责边界，不再部署 0.4B State Router Shadow。

```text
strong Planner/Reviewer（外部 OpenAI-compatible API）
                     │ contract graph / review
                     ▼
本地 GPU0：2.9B S60 Selector（只选一个 operation）
                     │ 已提交 operation
                     ▼
远端物理 GPU0：13.3B G3/G6 Executor（参数、执行推进、总结）
                     │
                     ▼
本地 Harness + Web UI + proactive worker
```

0.4B Shadow 没有通过毕业门，和已经训练、静态分类超过 96% 的 2.9B Selector 职责重复，
因此不启动、不进入前端、不参与路由或能力评价。旧源码和实验目录只作为历史审计证据保留。

## 当前固定身份

- Selector：`rwkv7-g1i-2.9b-vllm-v1`，S60 requirement-byte-tail，zero state，
  Hidden(mean+last)+h64 MLP；本地物理 GPU0；HTTP `127.0.0.1:29621`。
- Executor：`rwkv7-g1i-13.3b-exe-g3-g6-deterministic-cmix-r7-multiprofile-ctx2496`；
  远端物理 GPU0，服务端口 `18075`，本地 tunnel `127.0.0.1:29613`。
- offline task：`EXE-G3-MULTISTAGE-STEP2000`。
- network task：`EXE-G6-NETWORK-RECOVERY-STEP1500`。
- Planner/Reviewer：`gpt-5.4-mini`、strict JSON、reasoning `none`、无 fallback。
- Web：`127.0.0.1:8766`，静态资源为 Goal Studio；主动 worker 与 Web 使用同一 Product Controller。

G3/G6 根据不可变 retrieval policy 在 task 开始时只绑定一次，通过每个请求携带的 profile
ID/SHA 交给本地修改并验证过的 vllm-rwkv；run 内 profile switch 必须为 0。

## 启动与状态

先让远端 13.3B 服务和本地 `29613` tunnel 可达，再运行：

```bash
uv run rwkv-lh-stack up --web --worker
uv run rwkv-lh-stack status
```

`deploy --web --worker` 仍可作为同义的一命令入口；当前产品没有独立本地 engine prepare，
因此不会安装或启动 0.4B。

```bash
uv run rwkv-lh-stack deploy --web --worker
```

停止项目拥有的本地进程：

```bash
uv run rwkv-lh-stack down
```

`down` 只停止 PID、进程启动时钟、进程组和命令摘要共同匹配的项目进程。外部 13.3B 服务、
已采用的 SSH tunnel 和启动前已经存在的服务不会被停止。Selector launcher 调用 `exec(2)` 后，
manager 会在健康证明完成时以相同 PID/start time 刷新命令摘要，避免健康服务被误报为 orphan。

## `.env.local` 关键配置

```dotenv
RWKV_RUNTIME_MODE=external
RWKV_BASE_URL=http://127.0.0.1:29613/v1
RWKV_MODEL=rwkv7-g1i-13.3b-exe-g3-g6-deterministic-cmix-r7-multiprofile-ctx2496
RWKV_STATE_PROFILE_ID=EXE-G3-MULTISTAGE-STEP2000
RWKV_STATE_PROFILE_DELIVERY=request
RWKV_EXECUTOR_PROFILE_ROUTING=retrieval-policy-v1
RWKV_NETWORK_EXECUTOR_STATE_PROFILE_ID=EXE-G6-NETWORK-RECOVERY-STEP1500
RWKV_TOOL_DISCLOSURE_MODE=progressive
RWKV_SELECTOR_BASE_URL=http://127.0.0.1:29621
RWKV_SELECTOR_LAUNCHER=/home/chase/GitHub/RWKV-LH/scripts/run_network_selector_s60_requirement_byte_tail_zero_service.sh
```

完整 SHA-256、超时和强 Planner 配置见 [`.env.example`](../.env.example)。真实 API key 只放
ignored `.env`/`.env.local`，不进入文档、结果或运行日志。

Supervisor `.env` 只允许把 `SUPERVISOR_*` 注入进程；不能再覆盖 `RWKV_*`。这是组件级配置
命名空间边界，不依赖调用顺序或 Web 进程是否已经读取 topology。

## 健康证明

`rwkv-lh-stack status` 分别验证：

- 13.3B `/v1/models` 中的 served model；
- 2.9B `/healthz` 返回的 model、base SHA、head SHA、input protocol 和 state profile；
- manager 进程所有权与当前 PID 身份；
- 进程和健康拓扑中不存在 0.4B Router 项；历史进程记录只会在 `down` 时被安全清理。

部署烟测 `UI-20260830-233140-0dadf4` 已通过 Web POST 验证
`progressive → calculator → final_answer`，最终 `4` 与持久 RWKV 输出一致；完整回归为
`706 passed, 1 warning`。该烟测只证明服务链路，不替代 Agent Ladder。

前端的 `/api/runtime/topology` 另外展示 Planner、Selector、Executor 与 Harness 的真实拓扑；
它不把单元测试或历史 Round 分数伪装成当前服务健康。

## 已知边界

- OpenAI-compatible Executor 尚未声明完整 durable recurrent-state
  create/resume/fork/commit/rollback/export/import，因此会话上下文仍使用可审计 prompt replay；
  G3/G6 initial state 的 per-request 绑定已经独立生效。
- 静态 Selector 超过 96% 不等于真实多步 Harness 的同等成功率；发布能力必须看固定 Agent
  Ladder 的 completed/external/strict 三项结果。
- 远端 `18070` 是旧产品连续性服务，不能被本运行栈停止、替换或解释成 G3/G6 实验结果。
