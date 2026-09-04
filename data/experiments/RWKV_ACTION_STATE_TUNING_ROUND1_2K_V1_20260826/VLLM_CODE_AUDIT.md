# RWKV vLLM 代码与部署审查（2026-08-26）

## 结论

当前 vLLM 能正确加载 RWKV 基座和 Round1 state，原生 greedy/seeded sampler 可用，request
state 的初始注入会真实改变 logits。现有 Round1 未改变工具选择决策的根因不是 state 未注入，
而是训练后的 logit 位移尚未越过决策边界。

当前不能把远端 vLLM 源码标记为“完整通过正式测试”：源码树没有 `.git`，运行环境没有
`pytest`，而且源码中的原生 sampler 实现与一组旧测试断言直接冲突。下面区分已经修复的部署
缺陷、仍需修复的源码/测试缺陷，以及不属于 vLLM 根因的模型缺陷。

## 已验证的运行链

- 实际加载源码：`/home/chase/vllm-rwkv/vllm/__init__.py`。
- 源码版本：`0.23.1.dev0+rwkv.56b463bf69`。
- 服务环境读到的 distribution metadata：
  `0.23.1rc1.dev1352+g06c79080f.cu128.rwkv`。
- 运行源码树：4683 files、169846255 bytes、SHA-256
  `8709c7a4ff02e39a2b7a599a066ba0a6f33fe5e6dbe963e52601a6b13efa75d3`。
- 已加载 RWKV extension：`vllm/rwkv7_ops.abi3.so`，SHA-256
  `29631c7d14151129f965c666a5884b10c75b5469688382267f049de3b5df91a8`。
- v2 preflight 会导入实际的 `vllm`、`vllm.rwkv7_ops`，校验完整源码树和关键文件，
  不再以安装包 metadata 代替实际运行代码。
- A/B/A 因果复测为 tuned -> zero -> tuned；前后两个 tuned 的 12/12 内容、首 token、top20
  和 logprob 完全一致。zero 与 tuned 有 3/12 top20 集合变化，最大共同 token logprob 位移
  `0.4399871826171875`，证明 state 被消费；但 12/12 greedy 内容不变。
- `max_num_seqs=640 -> 64` 后 12/12 logits 与 c640 完全一致，EngineCore 显存约由
  67.35 GiB 降至 31.12 GiB。
- 原生 sampler 在线 smoke：temperature 0 的 greedy 和 temperature 0.8、seed 826 的 seeded
  各重复两次，均 HTTP 200 且结果完全一致。记录见 `vllm_native_sampler_smoke.json`。

## 发现的问题

### [P1] 运行源码与包元数据来自不同提交

`vllm.__version__` 指向 RWKV 提交 `56b463bf69`，但服务环境因源码根目录中的旧
`vllm.egg-info`，让 `importlib.metadata.version("vllm")` 返回提交 `06c79080f`。源码目录又没有
`.git`，因此普通的 `vllm --version`、平台判断和实验记录无法证明实际加载的代码。

当前风险已由源码树 digest 和关键二进制 digest 阻断，服务不会在代码漂移后静默启动；但这
只是部署栅栏，不是元数据根治。应从目标提交构建一次干净 wheel/editable install，删除陈旧
egg-info，要求源码版本、distribution commit 和构建 CUDA 后缀来自同一构建 manifest，并在
CI 中断言一致。

### [P1] RWKV sampler 实现与测试的协议相反

运行源码 `vllm/v1/worker/gpu/model_states/rwkv.py` 的 `custom_sampler` 明确执行
`sampler.require_rapid = False`，理由是 RWKV sampling 只消费 logits，原生 sampler 才能覆盖
greedy 与 per-request seed。服务也显式设置 `VLLM_USE_RAPID_SAMPLER=0`。

但 `tests/model_executor/models/test_rwkv7.py` 仍要求 `require_rapid is True`，并要求 rapid
不可用时抛出 `requires rapid-sampling`。另一方面，
`tests/models/language/generation/test_rwkv7_albatross.py` 又包含关闭 rapid sampler 的路径。
这不是运行实现失败，而是测试协议发生分叉；一旦恢复 pytest，该旧测试必然失败并使 CI
结论失真。

应以当前原生 sampler 能力为正式协议，改掉两条陈旧断言，并增加 greedy、seeded、top-k/p、
logprobs、并发 request isolation 的端到端回归。如果产品决定重新强制 rapid，则必须先证明
greedy 和 seeded 等 harness 路径不回退，不能只改实现布尔值。

### [P2] state tuning 通过 `sitecustomize` 修改私有方法

适配器会替换 `RWKV7ModelState.__init__`、`_zero_row`、`_new_dummy_state_tensors` 和
`reset_after_weight_update`。当前实现已被文件 hash、state hash、shape/dtype/finite 检查、运行
attestation 和 A/B/A 因果测试覆盖，因此本版本可用；但任一 vLLM 私有接口变更都会形成升级
风险。

长期应把 `initial_wkv_state` 做成 RWKV7 model state 的一等配置与加载器，在源码测试中覆盖
新 request、释放后复用、chunked prefill、mixed prefill/decode、并发、取消、preemption 和
weight update reset。完成前继续以完整源码树 hash 阻止未审查升级。

### [P2] OpenAI Chat tools 不是当前 harness 的可靠协议入口

原生 `/v1/chat/completions` 的 `tools + forced tool_choice` 不能稳定产生结构化 `tool_calls`；
在线 sampler smoke 也表明普通 Chat 提示会输出模型的推理前缀，而非严格遵循短答案要求。
这属于 chat template/tool parser 与模型协议的组合缺口。

RWKV-LH 当前使用的是 `ModelSession -> /v1/completions -> G1i JSON parser`，不依赖原生 Chat
tools，所以它不解释当前 harness 的 `select_tool` 误选。若未来对外宣称 OpenAI function-call
兼容，必须单独修 chat template、reasoning boundary 和 tool parser，并建立正式用例；不能用
`/v1/models` 健康检查代替。

### [P2] tuned/zero 共用基座别名会削弱可观测性

服务同时暴露 tuned 专用名称和基座别名，但本地客户端当前仍使用基座别名。请求确实进入
tuned 服务，却无法仅凭 response model 字段区分 tuned/zero。应让正式 state 实验使用 tuned
专用 served-model-name，并把 state SHA 写入每轮 run manifest/attestation。

### [P3] slow tokenizer 仅是性能警告

当前日志提示 slow tokenizer。它不会改变 state 或 sampler 的正确性，但高并发长 prompt 下会
增加 CPU 渲染/tokenize 开销。优化前需要固定相同 prompt/token ids 做性能消融，不能更换 tokenizer
后直接比较吞吐。

## 已修复的部署缺陷

- RWKV-LH 客户端曾继续使用旧 `vllm-rwkv-rapid` profile，因此即使服务已启用 native sampler，
  客户端仍拒绝 temperature 0 和 request seed。现已增加 `vllm-rwkv-native` profile，保留 rapid
  兼容模式，并让 native greedy/seed 进入真实 wire payload；单测和在线重复 smoke 均通过。
- API key 不再作为 `--api-key` 出现在 argv；改由权限 0600 的环境文件提供
  `VLLM_API_KEY`，当前启动日志无 `api_key` 字段。
- 曾暴露的本地凭据已轮换；本地和远端凭据一致，错误凭据返回 HTTP 401。
- 本地 `.env.local` 和远端环境文件均为 0600；历史实验快照中的凭据已脱敏。
- `max_num_seqs` 已从与 harness 不匹配的 640 降为 64，保持 16K context 与 98304 token
  batch budget。
- preflight 已从 distribution-only 升级为实际源码、完整源码树、extension、adapter、base 和
  state 的统一校验。

## 当前验收边界

可以开始下一轮 selector state-tuning canary，因为 vLLM state 注入、原生 sampler、部署安全和
资源配置都已证明可用。不能声称“vLLM 全量测试通过”：远端环境缺 pytest，且已知旧测试与实现
冲突。下一轮 state 数据必须针对 `select_tool` 决策边界；不能用新增工程路由规则掩盖模型误选。
