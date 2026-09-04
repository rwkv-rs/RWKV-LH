# RWKV Agent 状态链、执行权与 Goal 生命周期整改 V1 预注册

登记时间：2026-08-31（Asia/Shanghai）。本协议在正式真实项目母路径验收、全量回归和
部署能力复核前冻结。开发期定向测试不计入正式结果，也不作为调整阈值的依据。

## 1. 目标与系统不变量

本实验验证系统性架构约束，不针对单个提示或测试样例写特判：

1. RWKV Executor 的正常后继只向原生 recurrent state 追加本步 delta；不把历史 prompt
   重新拼接后发送。单次 bootstrap/delta 仍受 16K 输入边界约束。
2. WKV state 和 Selector state 都是可丢弃、可重建的加速缓存，`authoritative=false`；
   权威事实仅来自不可变 Goal、追加式 causal ledger、已接受 RWKV Decision 与 Harness
   Action/Result。
3. `exact_tool_selection_staged` 只是 operation 候选交接。Executor 必须在当前父状态、模型、
   profile、工具定义和 atom contract 下重新授权并消费它；在线链路不再产生
   `exact_tool_selection_committed`，缓存和 selection 都不能直接授权执行。
4. Goal 模式是 `self_termination_only`：预算、协议、动作和运行时故障只允许提交 checkpoint、
   yield 或等待恢复；只有显式 RWKV `final_answer` 决策可以完成 Goal。
5. 真实项目目录本身必须成为 Harness 的 `workspace_root`。所有 Action 参数保持相对路径，
   正常访问、失败恢复和越界拒绝都由同一生产 Harness 路径处理。

## 2. 固定数据、版本与生成方式

### 2.1 历史真实轨迹

来源：`FAST_AGENT_CAPABILITY_CANARY_V1_20260831/run_s60_g3_g6_post_closure_v1`。
版本/用途：修复前 S60+G3/G6 三题真实 causal ledger，仅做全轨迹反事实完成门审计，
不修改原始数据。

- L1 causal ledger SHA-256：`0e1150ca775c8e354513eb723715e2d13c27499d24bb416c56b3502db6e666e0`
- L4 causal ledger SHA-256：`52264bfedc6b39d137591e06f17f41c55fca4132a1116f6f061e053f5dd8479a`
- L5 causal ledger SHA-256：`5485929218aff185579bb399684f4636c3b99e3c4480ccea6c8d97b2578b056d`
- results SHA-256：`7e9a22f4bff2b90912533ceb5b93cbf7a24bdff8e4d63871f5802c1c4b49faef`

### 2.2 真实项目母路径数据集

来源：执行时的 `/home/chase/GitHub/RWKV-LH` 当前工作树；Git HEAD 固定为
`683528577298258d12d7ed0e09c3ae57aa8bbf16`，分支
`chase/hybrid-product-v1`。修复中的未提交文件按内容摘要纳入版本，不以 HEAD 替代实际内容。

生成脚本：
`/home/chase/GitHub/RWKV-LH/temp/run_real_project_native_state_parent_workspace_acceptance_20260831.py`
（SHA-256：`265636b68c74d59ddcd398f4c36941f1cc3a4e81edfbf4bea84a73699985f618`）。

固定复制范围：`.github/`、`benchmarks/`、`docs/`、`rwkv_lh/`、`scripts/`、`tests/`
以及 `.env.example`、`.gitattributes`、`.gitignore`、`AGENTS.md`、`LICENSE`、`README.md`、
`pyproject.toml`、`uv.lock`。固定排除 cache、bytecode、`data/`、`temp/`、`.git/`、`.venv/`、
`.env` 和 `.env.local`，避免历史实验、运行缓存或密钥进入模型工作区。

脚本在正式 run 目录首次创建时生成 `SOURCE_MANIFEST.json`，逐文件登记来源、用途、
生成方式、大小、SHA-256 和总 manifest SHA-256。工作副本路径固定为：

`data/experiments/RWKV_AGENT_LOOP_LIFECYCLE_REMEDIATION_V1_20260831/run_real_project_parent_workspace_v1/workspace`

该路径本身直接写入 `Goal.workspace_root`；测试动作不得作用于原项目目录。

### 2.3 整改代码冻结摘要

- `rwkv_lh/atom_execution.py`：`20e6aff8c1e506f7a2c772f712311bd17748ce8413e35a2be9243efc5084c495`
- `rwkv_lh/controller.py`：`0684634392ae1bd06f0b9c488142c5c410d5f7f0a0d80809faf7836f8ed6c66f`
- `rwkv_lh/model.py`：`c86322e87e0149d4eac23ad9b0f6a903463cfb0caba9180c654d8171097f203e`
- `rwkv_lh/model_session.py`：`5f27a6c0ecefaaf21248c6615d70818197a1e66e18ca699507c2c803ac2fa18e`
- `rwkv_lh/run_lifecycle.py`：`29a7b8f0da870696c0b6c9711a327732cafe512fa458f45225bbbe4b0633e76f`
- `rwkv_lh/runtime/native_state.py`：`79345298fb969be243dffb9a403417c5f09473feddee78965927d7355443f18b`
- `rwkv_lh/runtime/openai_compat.py`：`e5387de61d1793f82b2da0a7739d80a8b7f5be247838956514f20acc1b1c4d38`
- `rwkv_lh/runtime/protocol.py`：`4e28bacc34345f1bfb0802e8403cf298e18cf63ea471113d1cabd7aaa6e7d02e`
- `rwkv_lh/runtime/settings.py`：`492caf726d569ae87f0b3920ddf5547bdd3ca6433bd04f6bd0a83cd2d46014ef`
- `rwkv_lh/runtime/stack.py`：`92a23b81056504d8aa1e1cae99f15121a5b836f594549fb3ced70a3e8f8b1399`
- `rwkv_lh/schema.py`：`6e2072bfaa06137ed4bc8871aa6a27a934ec62d7bd05274d65ee0efeeb667ca1`
- `rwkv_lh/web_worker.py`：`70407c8cc556e59731eaf0c53cbc0f8108a2d513ba4fc7daac598eb6eee39392`
- `rwkv_lh/exact_tool_selector/network_client.py`：
  `a73bd7b0e8c319ea47ea4d1ed6aba8d0396f2f40f6716c7d7227d28a5204d35f`

## 3. 固定真实项目 Action 序列

语义输出由确定性 native-state protocol fixture 固定，只替代模型采样；Controller、Model、
`NativeRWKVModelSession`、Harness、SQLite Store、causal projection 和 bubblewrap 均走生产代码。
这个实验验证真实工作区执行与状态协议，不冒充 live RWKV 模型质量实验。

固定顺序和预期：

1. `list_directory .`：成功；
2. 在 `rwkv_lh/controller.py` 中 `search_text class LongHorizonController`：成功；
3. 读取缺失文件：失败；
4. 读取 `../AGENTS.md`：`ScopeViolation`；
5. 读取 `rwkv_lh/run_lifecycle.py`：成功，证明失败后继续；
6. 创建 `agent_acceptance/`；
7. 写入 `probe.txt`；
8. 追加文本；
9. 精确替换；
10. 复制为 `copied.txt`；
11. 移动为 `moved.txt`；
12. 读取 `moved.txt` 摘要；
13. bubblewrap 中用项目 Python 做只读内容断言；
14. 删除 `moved.txt`；
15. 显式 RWKV `final_answer` 完成。

最终 `probe.txt` 字节必须精确等于 `phase=verified\nphase=appended\n`，`moved.txt` 必须不存在，
原项目所选源文件总 manifest 在 Agent Action 前后必须完全一致。

## 4. 固定指标、算法与阈值

不使用主观相似度。所有行为检查按登记键逐位计算：

`exact_position_accuracy = true 检查数 / 全部检查数`

阈值固定为 `1.000000`，包括：母路径身份、源快照、操作顺序、成功/失败向量、恢复、越界拒绝、
最终字节、沙箱执行、原目录未变、Goal 完成来源、禁止终态、native-only transport、WKV
非权威、append delta 上限、generate 不携带 prompt、state chain 推进、fixture 输出耗尽、Selector
非权威和在线无 committed 事件。任一布尔位失败即该实验失败，不调整口径。

## 5. 固定回归门

1. 定向链路测试命令固定为：
   `uv run pytest -q -s tests/test_model_session.py tests/test_runtime_stack.py tests/test_web_ui.py tests/test_unified_controller.py tests/test_exact_tool_selection_handoff.py tests/test_independent_network_selector_integration.py tests/test_network_exact_tool_selector_client.py tests/test_openai_compat_runtime.py`。
2. 全量命令固定为：`uv run pytest -q -s`。通过阈值为 collected tests 100% 通过；收集数和
   精确结果在正式结果文件中登记。
3. `git diff --check` 必须通过；相关 Python 文件 `py_compile` 必须通过。
4. 历史 ledger 摘要必须全部匹配，历史 atom/outcome 扫描完整率为 100%。

## 6. 部署能力边界

live 主模型服务必须在 `/v1/capabilities` 明确声明完整 durable recurrent state 能力，且
`recurrent_state_protocol` 精确等于 `rwkv-lh.native-state.v1`。`native_required` 下缺失或版本不符
必须 fail closed，不能静默回退 prompt replay。部署探测只登记客观响应和 readiness，不把
protocol fixture 结果写成 live RWKV 结果。

只有真实项目 exact-position accuracy=1.0、定向和全量回归 100%、历史审计完整、部署边界
如实区分后，才可以宣称代码整改通过；若 live 服务未实现该协议，只能声明代码已 fail closed，
不能声明 live 原生状态链已经上线。
