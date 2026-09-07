# vLLM-RWKV Supervisor 请求格式只读审计

日期：2026-09-07。Agent 级：本子任务未运行 Agent 题目，未调用任何生成端点，不能据此报告 Strict / completed / mutation 改善。角色级：验证的是输入渲染、tokenization 和源码接口，未证明模型能遵守 Planner 或 StageChecker 的输出契约。

## 可实施结论

当前部署可使用正式 `/v1/completions` 接口，发送与引擎原生 `open_think` 模板完全相同的文本。Planner 的唯一请求构造函数与 system prompt 保持原职责，transport 仅把 system / 已序列化 user payload 包在原生格式中：

```text
System✿{system_prompt}✿
User✿{payload_text}✿
Bot✿<think
```

这里大括号是文本变量占位符。`payload_text` 必须来自现有生产 `_render_user_payload`，不能另造角色输入。完整字符串没有最后一个 `>`，这与部署的原生 renderer 一致。

向 `http://127.0.0.1:29613/v1/completions` 发送的核心字段如下；模型 alias 经本次 GET `/v1/models` 确认，地址为本地现有 tunnel：

| 字段 | 值 / 要求 |
| --- | --- |
| `model` | `rwkv7-g1j-13.3b-zero-state-capability-ctx16384` |
| `prompt` | 上述原生 open-think 格式，逐字保留 system / user 文本 |
| `max_tokens` | owner 已授权放大；本次核对 8192 输出预算与当前 1918 输入 tokens 相容 |
| `add_special_tokens` | `true`；实际得到恰好一个首 token 0 |
| `stream` / `echo` | `false` / `false`，读取本次 completion 文本 |
| `stop` | `["✿"]`；raw completion 不知道 Bot 模板，必须显式传入原生模板的文本 stop |
| `vllm_xargs.rwkv_state_profile` | `zero` |
| `vllm_xargs.rwkv_state_profile_sha256` | 64 个字符 `0` |
| `response_format` / `structured_outputs` | 均省略；否则仍进入当前缺依赖的 structured-output 路径 |

采样参数应由本轮既有配置明确绑定，不从其他角色的运行上下文暗中读取或切换。其他角色的 State / 会话与工具调用协议不应复用到 Planner。

响应使用 `choices[0].text`，不是 chat 的 `choices[0].message.content`。主代理已选择把响应严格绑定到本次实际发送的 `<think` prefill：检查正常 `finish_reason=stop` 和原始文本以 `>` 开始，再合回已发送的 `<think` 交原有 strict JSON decoder；记录 raw output、prefill 与 wire SHA。此为拟实施边界，必须由生产回归与主代理真实 probe 验证。本次没有执行这个生产 adapter，也不把任意后缀 JSON 扫描或补齐语义字段视为可接受方案。

## 部署项目的直接依据

引擎根目录：`/home/chase/GitHub/RWKV-LH/data/runtime/engines/vllm-rwkv-67f0c5996c50`。读取实际部署源码，全程未执行服务器 Git。

- `docs/getting_started/quickstart.md:166` 附近说明 raw generate 不会自动套 chat 模板，应先调用 tokenizer 的模板构造；`:232`–`:245` 提供 `/v1/completions` 的 `model/prompt/max_tokens/temperature` curl 示例。
- `vllm/tokenizers/rwkv_defaults.py:130` 的 `render_rwkv_chat_template` 是当前原生入口；`:276`–`:302` 将 plain system/user/assistant 对话原样渲染；`:369`–`:374` 明确 open-think 为 `<think`、fake-think 为 `<think></think`。两者最后一个 `>` 都由 completion 继续生成。
- `tests/tokenizers_/test_rwkv.py:135`–`:149` 断言多轮对话的精确 Bot 字节；`:263`–`:273` 断言 fake-think 精确尾缀。`tests/tokenization/test_rwkv_serving_contract.py:19`–`:68` 断言 raw completion 与原生 chat 的 BOS / token 序列。这些是已部署项目自带实现与测试证据，未重新运行这些测试。
- `vllm/entrypoints/openai/completion/protocol.py:45` 起接受字符串 prompt、max_tokens、stop、采样字段；`:294`–`:299` 与 chat 共享 `structured_outputs_from_response_format`。`completion/serving.py:139`–`:185` 使用 completion renderer 和 sampling params，不会再套 chat 模板。
- `rwkv_defaults.py:434`–`:453` 只在传入 prompt-template 对象时自动加模板文本 stop；raw `completion/serving.py:183` 未传该对象。因此 raw 必须显式保留 `✿` stop。引擎仍加入 EOS token 0，并强制 `ignore_eos=false`。

## 零生成实测与错误控制

1. **当前完整 canonical Planner 请求**：从已经保存的可见请求恢复 `GoalPlanRequest`，使用当前生产 `plan_goal_patch`，在其 HTTP 调用前截获唯一 system / payload，再由 `_render_user_payload` 序列化。没有手写角色协议对象，没有读取隐藏验收。输入来源、脚本和生产源码 SHA 均在 `CANONICAL_COMPLETION_PARITY_INPUT.json`。
2. **真实原生 renderer 对照**：用远端既有 engine Python，只构造 CPU tokenizer 并调用原生 renderer。拟定格式与 native 对当前完整请求 UTF-8 字节相同、全部 1918 token 相同、恰好一个首 token 0。prompt SHA 为 `59668f84325816b61a6069a5c463fc56bbe4d3adab8ea6f1e4fd7073ed46d0da`，token IDs SHA 为 `3889890ddb07edc525ba1a41b21aefbf77863dd6a88fa95425aeab57caea2794`。
3. **特殊字符边界**：独立 transport 控制包含 CRLF、引号、反斜线、`✿`、think 文本、中文、emoji。拟定格式与原生 renderer 字节和 41 token 全部相同。这证明继承当前原生保留文本的行为，不证明这些文字在模型语义层无影响。
4. **错误控制**：每个样本分别去掉 user 前分隔符、改成错误 assistant 标签，共 4 个错误控制全部在字节与 token 比较中被拒；2 个正确控制全部通过。这是本次格式一致性检查的正 / 负控制，不能冒称生产修复先红后绿 pytest 原始日志。
5. **实际 HTTP tokenization**：完整请求分别送 `/tokenize` 的 raw / native-chat 入口，再对 raw tokens 调 `/detokenize`。两入口 token IDs 完全相同，UTF-8 原文完整恢复；1918 + 8192 = 10110，小于服务公布的 16384。该事实仅适用于本次完整初始请求，不保证后续增长的计划 / 阶段证据仍在窗口内；不得用静默截断解决超长输入。

所有 HTTP 调用仅为 `/v1/models`、`/tokenize`、`/detokenize`。两个远端离线脚本均设置本诊断进程 `CUDA_VISIBLE_DEVICES=''` 并禁止网络与 Git，未加载模型、读取 State 内容或改动服务、引擎、venv。上传到远端的只有 `temp/` 分析脚本。

## chat 参数的已证实边界

`WIRE_TOKENIZATION_CONTRACT.json` 使用小型 transport 控制，结果均为 HTTP 200：

| 输入方式 | tokens | 观察 |
| --- | ---: | --- |
| 默认 native chat open-think | 25 | 尾缀 `Bot✿<think` |
| chat + `chat_template_kwargs.rwkv_generation_prompt=fake_think` | 25 | 与 open-think 逐 token 相同，参数未体现在实际渲染中 |
| 原生 renderer fake-think → raw | 27 | 尾缀 `Bot✿<think></think`，与 open-think 不同且逐字保留 |
| 最后 assistant 为 `<think></think>`，`add_generation_prompt=false`，`continue_final_message=false` | 29 | 尾缀 `Bot✿<think></think>✿` |
| 同上但 `continue_final_message=true` | 29 | 与 false 逐 token 相同，最终 message 仍带 `✿` |
| raw 显式闭合 fake-think 边界控制 | 28 | 原文保留；它不是原生 fake-think 函数的精确输出，未被选作本轮生产方案 |

对应源码：`vllm/renderers/hf.py:633`–`:665` 过滤模板 kwargs；`RWKVTokenizer.apply_chat_template` 在 `vllm/tokenizers/rwkv.py:369`–`:399` 把 RWKV 专用参数藏在 `**kwargs`，原生模板为无变量的 Jinja 注释。因此 fake-think 参数虽被请求 schema 接受，却未到达实际原生 renderer。`continue_final_message` 是 schema 支持的标准参数，但当前 RWKV 原生分支未使用它；原生 plain renderer 无条件封闭已有 message。不能仅凭 HTTP 200 宣称这些开关实现了期望的续写边界。

## Structured output 与 Zero State

换成 raw completion 不会自动修好 structured output。`completion/protocol.py:294` 与 `openai/engine/protocol.py:177` 共用格式归一化；只要带 json_object / json_schema，仍启用 SamplingParams 的 structured-output 校验。之前带 `--log-error-stack` 的实测第一错误是 lazy import `lmformatenforcer` 失败；独立 CPU 验证也发现 `xgrammar` 缺失。具体因果已冻结在上一连接轮的 `STRUCTURED_OUTPUT_IMPORT_FAILURE_FOLLOWUP.zh-CN.md`，本次未重复生成、未安装任何依赖。raw 省略约束参数后，JSON 合法性必须继续由模型能力和原 strict decoder / 角色契约验证。

Zero 字段的源码链：`completion/protocol.py:211` 接受 `vllm_xargs`，`:355` 与 `:392` 传到 `SamplingParams.extra_args`；`vllm/v1/worker/gpu/model_states/rwkv.py:40`–`:42` 定义两个字段名和 `zero`，`:77`–`:86` 注册 `zero` / 64 个 `0` / `wkv_state=None`；`:1247`–`:1280` 要求 ID 和 SHA 成对并比较注册身份；`:1374` 初始化请求行，`:1473`–`:1480` 清零并仅在非空训练 State 时复制。原生 State 读写还需要额外 native refs，拟定 Planner 请求不携带它们。这里为源码检查，tokenization 不进入 State 解析，不能用本次零生成结果冒充运行时 State attestation。

补充实际远端源码 SHA：

```text
ccf05d15ef481408bdeb4a175ed2efa937fec89720edeb24bd6a9a73ee73e0fa  vllm/v1/worker/gpu/model_states/rwkv.py
ad74f52bd263605051abd29e8e30ff4acd3465567ed149419b46e60514bcf79f  vllm/entrypoints/openai/engine/protocol.py
79115aa5a484de5158954fb0552cbe1cb2bd384bec4a9c711c1dcb3f99055481  vllm/sampling_params.py
```

## 证据索引

- `CANONICAL_COMPLETION_PARITY_INPUT.json`：`8c0daecabad74247bfebb2e89f1add8bf623f2fe4e989c13d12947a01837d033`
- `CANONICAL_COMPLETION_NATIVE_PARITY.json`：`b20d5e411eb70ef31b01b1f327bd1d02fb3f0d14e36cf0b1634fa9e91bbc6bdf`；包含 13 个部署源码 / 文档 / 测试文件 SHA。
- `CANONICAL_COMPLETION_HTTP_PARITY.json`：`827367e8c6fc29b9f101a3d6215c6b53e0cb59f768070f8c66e9924507b18461`
- `WIRE_TOKENIZATION_CONTRACT.json`：`2b7a90aa8e6849a6b19160331ac8206951a06224d277e14d3412d40230804f37`
- `DEPLOYED_NATIVE_RENDER_OFFLINE.json`：`bcb72d95743c052c004825353380519d7cabbd25ea2007cee5b02203fa518303`
- `temp/audit_vllm_rwkv_canonical_completion_parity_20260907.py`：`187282496ec028fa964711f5801d71a8d51e75724a80988726bc9286862a1f2c`
- `temp/audit_vllm_rwkv_supervisor_wire_render_offline_20260907.py`：`bb25dde3e1648834e93fc763b1be4782e43ffeb530e462571e61df39b84e259b`
- `temp/audit_vllm_rwkv_supervisor_wire_tokenize_20260907.py`：`30c5f31f2b71574dd1a11d00b7836d82f56ab981d1449134fd78df45ae428f7e`

两份 `*.stderr.txt` 均为 0 字节。其 SHA 及本报告 SHA 可见 `READONLY_WIRE_AUDIT_SHA256SUMS`。本子任务没有待修改生产文件；后续真实生成、生产回归、预算配置、上传与冻结由主代理独立记录。
