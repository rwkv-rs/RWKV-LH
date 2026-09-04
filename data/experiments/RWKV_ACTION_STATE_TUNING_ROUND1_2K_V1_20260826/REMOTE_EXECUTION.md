# Round1 2K 远程执行边界

## 已只读确认的环境

- SSH alias：`rwkv-8222`；实际用户 home 为 `/home/chase`。
- RWKV-PEFT：`/home/chase/chase/RWKV-PEFT`。
- 本轮远程数据目录：
  `/home/chase/chase/RWKV-PEFT/data/rwkv_lh_action_state_tuning_round1_2k_v1/`。
- 基座：`/home/chase/weights/BlinkDL__rwkv7-g1/rwkv7-g1i-13.3b-20260805-ctx16384.pth`。
- vLLM-RWKV 环境：`/home/chase/.venv-vllm-rwkv-8e90d04ecb`；源码
  `/home/chase/vllm-rwkv`。
- GPU 资源：固定 GPU0；用户已授权停止其账号在 GPU0 上的任何现有任务，本轮优先。
- 当前原始基线服务：GPU0 / port 18070。数据未验收前保持运行；训练启动前停止并记录状态。
- state-tuned 部署：训练完成后复用 GPU0；端口与 service 名在启动前冻结并写入运行 manifest。
- state 注入适配器：`/home/chase/.local/share/rwkv-state-tuning-adapter/sitecustomize.py`；
  使用 `VLLM_RWKV7_INITIAL_STATE_PATH`。

认证信息不写入实验记录、数据 manifest 或训练包。上传前只创建本轮专用目录；不会覆盖已有
Round71 数据或 checkpoint。已有 GPU0 服务只在本轮训练/部署实际需要时停止。

## vLLM-RWKV 推理前置审计（2026-08-26）

- Python `3.12.3`，PyTorch `2.11.0+cu130`，vLLM
  `0.23.1.dev0+rwkv.56b463bf69`。
- GPU0 为 RTX PRO 6000 Blackwell 96GB；当前基线 EngineCore 使用约 96.6GB。
- 原始基线参数：`VLLM_USE_V2_MODEL_RUNNER=1`、`VLLM_RWKV7_WKV_MODE=fp32io16`，关闭
  rapid/flashinfer sampler；`max_model_len=16384`、`max_num_batched_tokens=98304`、
  `max_num_seqs=640`、`gpu_memory_utilization=0.98`、默认 temperature `0.1`。代码审查后
  state-tuned 正式服务把 `max_num_seqs` 固定为 64；12 条 c640/c64 logprob 因果探针完全一致，
  EngineCore 显存约由 67.35 GiB 降为 31.12 GiB。
- RWKV tokenizer 与 `rwkv` tool-call parser 已在启动参数中启用。
- 已有 state checkpoint 实测为 61 个 `blocks.<layer>.att.time_state`，每个
  `(64,64,64)`、bf16、全 finite。adapter 会转置最后两维后注入每个新 request 的 WKV 初始
  state；shift state 和 elapsed counter 清零。
- `/v1/models` 与项目实际 `/v1/completions` 路径健康；progressive selector 和 direct call
  均可被当前 parser 精确解析。
- 部署前置检查已升级为 v2：校验实际 import 的 vLLM 源码根、完整源码树 digest、关键 Python
  文件和 `rwkv7_ops` extension，不再以 distribution metadata 代替运行代码。详细审查见
  `VLLM_CODE_AUDIT.md`。

### 必须避免的错误验收

原生 OpenAI `chat/completions` 的 `tools + forced tool_choice` smoke 在当前 RWKV chat template
下没有返回结构化 `tool_calls`。RWKV-LH 实际不依赖这条路径：它由 Controller 渲染完整 G1i
prompt，通过 `/v1/completions` 取得原始 JSON，再由本地协议 parser 验证。

因此部署门必须使用真实 `ModelSession -> /v1/completions -> parse_tool_selection ->
render_tool_disclosure -> parse_model_command` 链；不得用 `/models` 健康或 Chat 原生 tool-call
smoke 冒充 Harness 可用性。若未来改用原生 Chat tools，需要独立修复 chat template/parser 并重新
预注册，不能静默切换。

### GPU0 部署约束

当前 GPU0 基线是 transient user unit。停止后不能假定其 unit 文件仍可恢复；训练前先记录完整
ExecStart/environment，Round1 部署使用新的持久 user unit。该 unit 必须显式设置：

- `CUDA_VISIBLE_DEVICES=0`；
- `VLLM_RWKV7_INITIAL_STATE_PATH=<selected checkpoint>`；
- `PYTHONPATH=/home/chase/.local/share/rwkv-state-tuning-adapter:/home/chase/vllm-rwkv`；
- 与 GPU0 基线服务互斥；
- 基座、16K 上下文、RWKV tokenizer/parser 和采样配置与基线一致，唯一模型变量为 initial state。
