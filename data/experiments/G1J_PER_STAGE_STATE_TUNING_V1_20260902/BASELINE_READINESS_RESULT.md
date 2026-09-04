# G1J per-stage State Tuning v1：初始 zero-State baseline readiness 结果

结果时间：2026-09-02T13:33:00+08:00。

## 最终判定

- State Tuning 状态：`NOT_STARTED`。
- 训练 State、选择 State、默认非零 profile：均为 `0`。
- Readiness：`FAIL_CLOSED`。
- 五个正式 zero-State Dev：`NOT_RUN`。
- 全 zero Agent Ladder：`NOT_RUN`。
- 可比较数值基准：尚未产生；不得把 `NOT_RUN` 记为 `0` 分或模型失败。

原因不是基础工程或 13.3B 服务不可用，而是冻结协议要求的 Gate 0 角色拆分、新 Selector Head、五个 renderer、五个生成器/evaluator 和五套正式数据尚未形成。按预登记停止规则，本轮不得绕过先决条件调用旧 Head、旧 State 或历史实验结果。

## 冻结工作区身份

- WSL：`UbuntuRecovered`。
- branch：`chase/rwkv-goal-loop-v2-cleanup`。
- commit：`9ae5eda1b8c5196ef401b62414e7d9ffd9243120`。
- tracked diff SHA-256：`65ab18f8e5e529891c9faf7b3c0520178fa8f9907bc70c4dd7a8768c316d26c8`。
- 本轮没有修改产品源码；只更新 ignored `.env.local`、增加 `temp/` 验证工具并写入本实验记录。
- 用户已有 tracked/untracked 工作区状态被视为本次冻结快照；未恢复、删除或覆盖。

## G1J 角色配置

Executor：

- model：`rwkv7-g1j-13.3b-zero-state-capability-ctx16384`。
- base weight SHA-256：`559371f5b9aef13189ae54b345ac096af4ad2b689996c05d89de687612b3ae65`。
- endpoint：本地 `http://127.0.0.1:29613/v1`，经 SSH alias `rwkv-8222` 转发远端 `127.0.0.1:18234`。
- backend：`vllm-rwkv-native`；`state_transport=native_required`。
- profile：`zero`；profile SHA-256 为 64 个 `0`。

Selector：

- model：`rwkv7-g1j-2.9b-vllm-v1`。
- prepared artifact SHA-256：`c1a316e75abd50f5edc3358fbb2c7d1cb18c611d9b2aa5b888091c8d45cc866c`。
- input protocol：`rwkv-lh.exact-tool-selector-input.v8-frontier-question-tail`。
- feature protocol：`rwkv-lh.vllm-rwkv-final-hidden-mean-last-concat.v1`。
- profile：`zero`；profile SHA-256 为 64 个 `0`。
- 新 V8 Head SHA/Head hash：均为空；因此加载真实部署配置后 `NetworkExactToolSelectorSettings.from_env()` 按设计以非零异常 fail closed。
- GPU 3 仅登记为将来的 Selector 设备；本次没有启动 Selector。

`.env.local` 中不再保留旧 G1I 模型绑定。旧通用 API key 名只作为 secret compatibility fallback 保留，不承载模型、Head 或 State 身份。

## 非模型验证

### Agent Ladder catalog

命令：`uv run rwkv-lh-e2e --suite agentladderv1 --validate-only`。

结果：`tasks=10`、`selected=10`、`catalog_valid=true`。冻结套件包含 tier 1 至 tier 5，每级 2 个项目任务；本轮只验证目录和身份，没有执行任务。

### 源码测试

直接加载真实 `.env.local` 的首次全量结果是 `49 failed / 733 passed`。全部首错共享同一环境污染：测试 fixture 注入 legacy `RWKV_*` 模拟值，而 canonical `RWKV_LH_*` G1J 部署值已经由 `.env.local` 注入，角色配置的冲突检测正确 fail closed。

把 `.env.local` 临时移动到 `temp/env_local_source_test_isolation_20260902`、在 shell trap 中保证原样恢复并校验恢复前后 SHA 后，执行：

`uv run pytest -q -s`

结果：`782 passed / 1 warning / 0 failed`，用时 `180.57s`。唯一 warning 是 Python 3.13 多线程进程调用 `fork()` 的弃用提示。部署配置恢复后的 SHA-256 为 `998862797d35f00608c383dee73623108609fc4fd74f03c308603f251bec74b5`。

结论：源码结构测试在部署配置隔离后全通过；测试 fixture 尚未隔离 canonical role env 是独立的测试环境缺陷，本轮按“不修改代码”约束只记录，不整改。

## 服务器与 zero-State native capability

连接与资源：

- SSH alias：`rwkv-8222`；远端 hostname：`rwkv-260304`；user：`chase`。
- GPU 0：`GPU-1faf7f09-25f4-2515-b707-6e0766aa841d`，RTX PRO 6000 Blackwell，97887 MiB。
- GPU 3：`GPU-a9570da2-547a-c2b3-0cab-7bbdc1a8a8b0`，RTX PRO 6000 Blackwell，97887 MiB。
- GPU 1/2 未探测、未停止、未复用。

仅在 GPU 0 启动 G1J 13.3B；未设置 `VLLM_RWKV7_STATE_PROFILE_MANIFEST` 或其 SHA。服务使用：

- vLLM build：`0.23.1.dev0+rwkv.56b463bf69`。
- WKV mode：`fp32io16`。
- max model len：`16384`。
- weight load：`267.72s`；总冷启动约 `620s`。
- model memory：`25.59 GiB`。

只执行 `/v1/models`、`/v1/capabilities` 和一次 `/v1/state/create`，没有调用 `/v1/state/generate`、chat 或 completion。全部断言通过：

- 精确 model identity；
- `rwkv-lh.native-state.v1`；
- create/resume/fork/commit/rollback/export/import 全部为 true；
- `prompt_replay=false`；
- cache `authoritative=false`、`cache_role=disposable_acceleration`；
- create export 回显 `state_profile_id=zero`；
- create export 回显 state profile SHA 为 64 个 `0`。

探针结束后已按启动 PID 和完整 command line 校验停止服务。GPU 0/3 均恢复为 `15 MiB / 0%`，端口 `18234` 不再监听。运行日志和一次性 cache 保留在远端项目 `temp/`，不属于训练 State 或发布 profile。

## Gate 0 完整性

以下固定模块全部缺失：

- `rwkv_lh/goal_state_protocols/__init__.py`
- `rwkv_lh/goal_state_protocols/selector_intent.py`
- `rwkv_lh/goal_state_protocols/executor_args.py`
- `rwkv_lh/goal_state_protocols/auditor_step.py`
- `rwkv_lh/goal_state_protocols/finalizer_answer.py`
- `rwkv_lh/goal_state_protocols/auditor_final.py`

以下固定生成器全部缺失：

- `scripts/generate_g1j_selector_intent_state_tuning_v1.py`
- `scripts/generate_g1j_executor_args_state_tuning_v1.py`
- `scripts/generate_g1j_auditor_step_state_tuning_v1.py`
- `scripts/generate_g1j_finalizer_answer_state_tuning_v1.py`
- `scripts/generate_g1j_auditor_final_state_tuning_v1.py`

同时缺少与新 V8 输入匹配且冻结身份的新 G1J Selector Head。协议规定 Gate 0 未通过时后续生成器必须非零停止；所以五个 Dev 和 Agent Ladder 没有合法输入，也不能产生对照分数。

## 当前可称为哪种程度的 Agent

当前项目处于“Agent 基础设施可验证、执行模型服务可用、产品 Agent 尚未满足启动门禁”的阶段：

- 可以证明 Controller/Harness/ledger 等源码回归通过；
- 可以证明 G1J 13.3B 零 profile 原生 recurrent-state transport 可工作；
- 不能证明 Selector、Executor-Args、Step Auditor、Finalizer、Final Auditor 五角色的端到端行为；
- 不能把它归入 Agent Ladder tier 1，也不能说是 tier 0 或 0 分，因为正式运行被实验协议主动阻止。

后续实现 Gate 0、新 Head、五个 renderer/generator/evaluator 和固定数据后，必须先在相同模型、Head、prompt、parser、verifier、采样参数和阈值下补跑“五个 zero-State Dev + 全 zero Agent Ladder”。那一轮数值才是 StateTune A-I 消融的正式分母；本结果是它的不可替代 readiness 前置快照。
