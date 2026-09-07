# 基线生产 trace 对 StateTune 的可用性审查

日期：2026-09-07。范围：本地生产源码、benchmark runner 源码、普通单元测试；未读取 acceptance、confirmation、Holdout 或封存内容。此文件只记录审查，不修改生产或测试代码。

Agent 级：本审查没有运行 Agent，没有新增 Strict / completed / mutation / 终止原因结果。

## 结论

现有 durable RunState 能保留成功发起的生成所使用的 checkpoint、父链、事实和输出，为先运行 zero-state 基线提供原始材料。不能直接将 `causal_ledger.requests[].input.prompt` 当作完整 StateTune 输入；native 路径在此只导出最后一个 delta。未来抽取器必须按真实 State 生命周期重建完整输入，调用当前角色 builder+renderer 验证正文，并逐行核对 SHA、因果顺序和标签权威。

这里的“可以重建”是对已持久化成功调用路径的源码分析，尚未用实际基线执行逐行重算，不等于已完成数据集验收。`role_trace_dataset_v1.py` 当前仍未实现。

## 各角色现有字段

| 角色 | 输入、事实与边界 | 输出和身份 |
|---|---|---|
| Selector | 三个菜单顺序各自的完整 bootstrap + step transcript；current subtask/progress、eligible labels；checkpoint/menu/input digest | 各 lane 原始 decoder trace、选择结果及最终 ensemble；模型/State/decoder/协议身份及 SHA |
| Executor | assignment 中的 constraints、workspace manifest、recent exact action records；v4 披露 delta 中的 requirement、execution state、工具合同、committed fact refs、history；checkpoint 父链、event IDs、cache binding | 原始文本/token IDs、sampling、finish reason、正规化、参数 provenance、接受/拒绝；模型/State/协议 SHA；selection/decision/action 绑定 |
| Step Auditor | 完整 bootstrap prompt；active step、boundary、evidence records、共享 builder 生成的 gap catalog；durable audit boundary | 原始生成、解析结果、kernel 接受/拒绝；audit/request/checkpoint 关联及模型/State/协议 SHA |
| Finalizer | 完整 bootstrap prompt；goal、completed steps、committed facts、evidence records | 原始生成、命令/decision、正规化；模型/State/协议 SHA |
| Final Auditor | 完整 bootstrap prompt；completed steps、evidence、Finalizer candidate、gap catalog | 原始生成、audit 决定、kernel 接受/拒绝；boundary/request/checkpoint 关联及模型/State/协议 SHA |

`RunState.to_dict(include_projections=False)` 仍包含全部 `model_states`；`LongHorizonStore.save()` 将其写入 runs 与 checkpoint 快照，并追加 causal event。benchmark 使用 `checkpoint_retention=100_000`，导出 `model_trace.json`、`event_log.json`、`state_timeline.json.gz`、`causal_ledger.json`，并保留 SQLite store。

## 已确认的缺口与处理边界

1. **native 最后 delta 被命名为完整 prompt。** `NativeRWKVModelSession._append_text()` 的新 checkpoint.transcript 仅为 suffix；benchmark `_causal_ledger()` 按 input checkpoint 直接取该字段。Executor assignment 中真实事实前缀因此不在该导出字段。父 checkpoint 和 state timeline 尚在，属于导出/抽取语义缺陷；保留完整原始工件后可以离线处理，不需要仅为此改变模型或重跑基线。

2. **native request 的角色类型缺失。** native `generation_started` 没有 `lane_kind`，而 ledger 由该键生成 request_type，结果可能为 `_lane`。role session audit hook 已添加 `model_role`，输入 checkpoint 也有 lane_kind，可据此准确识别。不得把 `_lane` 当作合法角色名进入训练集。

3. **角色 renderer 正文不是完整生产上下文。** 所有生成角色还使用 session bootstrap，Executor 尤其依赖其中的 workspace manifest 和精确事实。只重放 `render_generation_prompt(source)` 将改变 WKV 上下文。训练输入需要绑定真实前缀/State 初始化；协议正文必须由唯一 builder 生成，不能另造一套协议。

4. **Selector 失败请求未提前持久化。** native Selector client 发出请求后，只有成功响应才创建输入 checkpoint；ensemble 的原始 lane 输出在最终 handoff 才集中写入。如果网络失败、响应身份不符或某个 lane 中断，该未完成请求可能没有完整已持久化输入和输出。应明确标记缺失并排除训练，不能补造模型响应。若本轮要求每个失败请求也逐字节可复盘，需要在运行前补齐请求边界的 durable 记录。

5. **重建不能盲目拼接 parent transcript。** prompt_replay checkpoint 已保存完整串；native checkpoint 多为 delta，但 rollover 会从 fresh State 重建，同时保留历史 parent ID。应使用 transport、cache_binding、State chain digest、parent_state_digest 和 rollover 事件确认实际重置点，fork 延续与零 token acknowledgement 也需准确处理。生成后 State 的重放还须使用保存的 raw token IDs，并处理传输裁掉 stop suffix 的事实，不能仅凭显示文本猜测 token 序列。

6. **JSON trace 文件不是实时持久化日志。** benchmark 的 model_trace 在内存收集、case 收尾时写入 JSON；异常硬退出可能丢失尚未写出的工具 trace。SQLite causal 事实和已有 checkpoint 可提供部分恢复，但不能据此假定所有失败请求都有完整记录。收尾成功与文件 SHA 应纳入源 run 验收。

## 本轮基线必须保留的工件

- 每题完整 SQLite store 和已导出的 state timeline；不能只留评分汇总或 `input.prompt`。
- 原始 model trace、event log、causal ledger；请求/选择/动作/audit 边界身份和原始输出/token IDs。
- 当前代码、协议、模型、State、decoder 及运行参数的身份 SHA；运行结束的工件 SHA。
- 所有缺失输入、缺失输出、重建失败、传输失败的显式排除记录。没有合法标签时丢弃，禁止自行发明替代动作。

数据冻结/训练前，逐行检查必须证明 source 时点之前的 durable facts、实际输入、builder 重算正文、完整前缀/State 初始化和输出相互绑定；dev/confirmation 按固定 project family 切分，后续不再重生。

## 关键源码定位

- `rwkv_lh/schema.py`：ModelCheckpoint、RunState.to_dict。
- `rwkv_lh/store.py`：save、checkpoint_records。
- `rwkv_lh/model_session.py`：CandidateGeneration.raw_record、native bootstrap/_append_text/generate/rollover/fork。
- `rwkv_lh/model.py`：各角色 build_prompt_source、_session_attestation、_executor_prompt_source、_assignment、_advance_selector_lane、_select_tool_independently。
- `rwkv_lh/stateful_goal_loop.py`：execution state、goal action assignment、audit boundary 的打开/解决。
- `rwkv_lh/exact_tool_selector/native_network_client.py`：select、_checkpoint。
- `scripts/run_rwkv_e2e_benchmark.py`：role trace hook、_state_timeline、_causal_ledger、每题最终导出。

## 审查时源码 SHA-256

以下仅散列显式列出的源码，不读取任何数据集或封存文件；由 `temp/record_trace_readiness_source_sha_r1_20260907.py` 生成。

| 源码 | SHA-256 |
|---|---|
| `rwkv_lh/schema.py` | `e98a378d2c408e90d09e9578c2e089cec02054ea104da885079914d07d12acf6` |
| `rwkv_lh/store.py` | `c503e9424f9124d59f42b1647227bb5629933a7e5830fd2a67290d506a73f6b7` |
| `rwkv_lh/model_session.py` | `a84acb2d6b35c94fc7abd719a46f7c0deec6aaa8eb5ad1595a4e6cbf9825350a` |
| `rwkv_lh/model.py` | `5d995a19f834c03b38d73649796c6009cd8aad63f2e33e246b6c985e1df77095` |
| `rwkv_lh/stateful_goal_loop.py` | `dfd87e18d3fe57454812a492ee8070f3cafeaeee71f2c661e689d907982d9245` |
| `rwkv_lh/exact_tool_selector/native_network_client.py` | `9e71d88c8d96e9da4a68bff621dc8482832df7412ec73690389c2fd8391c36dc` |
| `rwkv_lh/exact_tool_selector/native_network_protocol.py` | `559d272ea4f28902679741e73640a4bbe49ebaabab52da80cd005388ff066db1` |
| `scripts/run_rwkv_e2e_benchmark.py` | `7f56fc1c50c415fd9e6f4572e25d40d777ea06e5ec29f8610c40b71f12263ee6` |
| `rwkv_lh/goal_state_protocols/selector_intent_v4.py` | `c94459290c44329f23bb74502b325bf9bceeb6cb4d831af6e75598cd3de1c10f` |
| `rwkv_lh/goal_state_protocols/executor_args_v4.py` | `4aec4e16bf839ea87e4be95b628e6a077300aab7f3db72bd5736e4b8fa3bc5ed` |
| `rwkv_lh/goal_state_protocols/auditor_step_v3.py` | `f718535e650da402cebba04274c2658c04f8f0df072d45a50bbd94500a73c2e9` |
| `rwkv_lh/goal_state_protocols/finalizer_answer.py` | `d42a6c3e9bcec48210caaab52dfdb18fc4d976bae2a57ee0cd177ce21f8671de` |
| `rwkv_lh/goal_state_protocols/auditor_final.py` | `bd475596f15ab3187a5653e703cffedb9a5f1d05953f3fd933422f255b3d4b48` |
| `rwkv_lh/exact_tool_selector/native_network_service.py` | `5970e648ac6086d38b17974472ccab79d57ffa9b7b284cb7978d3120d72e5114` |
| `rwkv_lh/inference/vllm_rwkv.py` | `6ab3a40722845e0d712c86ed908f6f931139613ffd6266b5c4ac1e831a755a8f` |
| `rwkv_lh/state_router/local_backend.py` | `867486623bde5c17d7a6f32b2cfa517ecb94f268bda75b744d735a781143515d` |
