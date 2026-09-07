# 本地 13.3B 接入 Planner / Stage Checker 的只读审计

本审计未修改生产源码、测试、配置、engine、venv 或服务，未加载模型、生成 token、读取 State 内容、SQLite 或封存题集，未在服务器执行 Git。只读源码、指定服务日志与三个 CPU tokenizer/parser 诊断的作者脚本在 `temp/`；服务器只执行同绝对路径下上传的脚本。主代理的实际 HTTP 探针和其后增加错误日志的 launcher 调整属于主代理记录，本报告不将其冒称为本审计操作。

接入尚不能仅以 GET `/models` 成功判定完成。主代理保存的 `EXISTING_WIRE_PROBE.json` 显示原格式 POST 立即返回空 message HTTP 500；本审计复制的原服务最近五分钟 journal 仅包含 GET 200 和 POST 500 两行，没有 traceback。此日志绑定 `rwkv-lh-current-zero-executor-20260907.service`，没有查询其他服务。服务器 `serve/utils/server_utils.py:392` 的通用异常处理在未开 log_error_stack 时只返回错误对象，即使开启，该通用分支本身也只 logger.error 记录请求 ID；不能从空错误文本准确反推出异常类型。

## 配置与角色边界

`SupervisorAPISettings`（`rwkv_lh/supervisor_openai.py:160`）只有一个 base_url / api_key / timeout，Stage Checker 只有独立 model。没有独立的 Stage Checker base_url、api_key 或采样配置入口。`RWKV_LH_STAGE_CHECKER_BASE_URL` 即使存在也不会在此读取。

| 配置项 | 使用同一现有 13.3B 服务时的要求 |
| --- | --- |
| RWKV_LH_PLANNER_BASE_URL | `http://127.0.0.1:29613/v1`（现有本地 tunnel，映射服务器 18234） |
| RWKV_LH_PLANNER_MODEL | `rwkv7-g1j-13.3b-zero-state-capability-ctx16384` |
| RWKV_LH_STAGE_CHECKER_MODEL | 同一个实际 served alias；不能保留原 Claude 名称 |
| RWKV_LH_PLANNER_API_KEY | 此 Settings 要求非空；无认证 loopback 服务应使用明确的非秘密占位值，无须沿用中转凭据 |
| RWKV_LH_PLANNER_FALLBACK_MODELS | 留空以明确本地模型路由，避免失败后请求其他 alias |
| RWKV_LH_PLANNER_MAX_PLAN_TOKENS | Planner 当前预算 1800 |
| RWKV_LH_PLANNER_MAX_CONTRACT_REVIEW_TOKENS | 当前 Goal Stage Checker 实际使用的预算，默认 2400 |
| RWKV_LH_PLANNER_PLAN_CACHE_ENABLED | 比较实验保持 false，避免重放已缓存的 Planner 产物 |

`role_config.py:11` 对同时存在但不相等的 canonical 与 SUPERVISOR 旧环境绑定拒绝运行；本地 env 文件不会覆盖已有进程变量。因此接入时须保证相应旧变量不存在或同值。配置核验应读取 settings.public_dict，不能打印实际凭据。

`goal_plan` 与 `goal_stage_review` 仍调用原有协议构造函数及本地语义验证；模型来源改变不会将 Planner 改成 Executor 或让 Stage Checker 接管 Final。共享模型名时，客户端的 circuit 状态也共享同一个 model key（`_request_json`），一个角色的失败可能暂时使另一个角色跳过同一模型，属于共享服务的相关故障边界。串行锁只覆盖 Supervisor 请求，不协调其他 native endpoint 请求；题级并发为 1 可降低资源竞争，但不能把默认采样称为确定性。

## 模板、JSON mode 与离线证据

Supervisor 的 `_wire_request` 目前发送固定 chat completions 格式：model、system/user 两条 messages、max_tokens、response_format=json_object。没有 temperature/top_p/seed，也没有 chat_template_kwargs / extra_body 配置入口；未被代码读取的环境变量不能改变这些字段。`.env.example` 的 Planner Responses 注释与当前代码不一致，当前 `_RESPONSES_API_PHASES` 为空。

实际服务器 engine 的 `tokenizers/rwkv.py:375` 和 `rwkv_defaults.py` 在原生函数中定义以下模板参数；这不表示它们已穿过完整 HTTP 渲染链路：

- `chat_template_kwargs.rwkv_generation_prompt` 仅允许 `open_think`、`fake_think`。默认 open_think 的生成前缀是 `<think`；fake_think 是 `<think></think`。这两个原始字符串的最后都没有 `>`。
- `chat_template_kwargs.rwkv_prompt_template` 可选精确值 `\nBot✿`、`\n\nAssistant: `、`\n### Assistant`；改变角色标记风格不会消除上述 think 前缀。
- 默认 Bot 风格把普通 system/user 转成 `System✿...✿` / `User✿...✿`，最后接 `Bot✿<think`。原生分支不使用 `enable_thinking=false` 代替 rwkv_generation_prompt；不存在已注册的 `none` 或裸 JSON 模式。

补充实际渲染证据：负责 tokenization 的另一子代理随后确认 open_think、fake_think、非法 mode 三种 `/tokenize` 请求均返回 200、1984 tokens、完全相同 SHA 和 `Bot✿<think` 尾缀；关闭 add_generation_prompt 则生效。其证据 `TOKENIZATION_KWARGS_RENDER_COMPARISON.json` SHA `63181b05a9727676925c75e1ead08aa0a8f1ef577a008d3976266d5506baf5f8`。源码根因是 `vllm/renderers/hf.py:633` 的 kwargs 过滤只保留显式形参/Jinja 变量/HF 通用参数，而 RWKV 专有键藏在 `**kwargs`，默认原生模板又仅有 Jinja 注释。因此当前 fake_think **不能作为已经可用的服务参数修复**；此前仅依据原生函数签名提出的候选已被实际渲染证据否定。本审计没有修复该链路。

`response_format=json_object` 在 `entrypoints/openai/engine/protocol.py:179` 转为 StructuredOutputsParams(json_object=True)，进入结构化输出路径；这是服务约束，不是客户端对输出 JSON 的普通解析。CPU 诊断给出：

| 离线验证 | 实际结果 | 结论边界 |
| --- | --- | --- |
| 使用现有 engine Python 构造 RWKVTokenizer，再导入 Xgrammar | tokenizer 成功；`ModuleNotFoundError: No module named 'xgrammar'` | 该环境的 Xgrammar 路径不可用；未到 TokenizerInfo.from_huggingface，不能将空 HTTP 500 的精确位置冒称为该调用 |
| 构造已注册 DeepSeekR1ReasoningParser | RuntimeError，找不到完整 think 标记的词表 entry | `<think>` token IDs 为 [61,35762,63]，`</think>` 为 [754,35762,63]；不是该 parser 构造要求的单 token |
| 导入已注册 Qwen3ParserReasoningAdapter，用已保存 WIRE_MINIMAL 响应做离线拆分 | 导入失败：`ModuleNotFoundError: No module named 'ijson'`，来自 registered_adapters 同时导入 MistralParser | 未进入 parser 构造或抽取，不能声称它已兼容或建议直接启用 |

Registry 没有 rwkv 专用 reasoning parser。DeepSeek R1 的非流式文本算法确实允许输出缺少起始 think，但该算法在当前 tokenizer 下无法按正常构造路径使用。Qwen3 的 engine adapter 从源码看允许可选单 token ID、使用文本标记，也保持 reasoning-only adapter 不解析工具；其正常导入路径在现环境缺依赖。没有补依赖、绕过构造、宽松处理输出、创造新模板或推荐此时修改 server。

## State、采样和身份

Supervisor 不发送 native State 引用、导出信息或 state_profile 参数，也不维护角色 WKV continuation。服务器当前普通 chat 新请求走 `v1/worker/gpu/model_states/rwkv.py:add_request`；服务启动未设置 State profile manifest 时选 zero_only，新的 row 经 `_initialize_row` 清零，再按请求明确指定的 native 引用或匹配缓存恢复。Supervisor 请求没有这些 native 引用，故不会承接 Executor / Auditor 的 native 会话 State；共享权重和 GPU 不构成请求间 State 共享。若以后服务改成加载角色 State 的默认 profile，Supervisor 客户端本身没有权重/State 验证机制阻止该变化，必须由外部冻结的服务身份保证。

审计开始时的 launcher 绑定 ctx16384，override-generation-config temperature=0.1；模型 generation_config 只含元数据，没有覆盖 top_p/top_k。聊天协议缺省 top_p=1、top_k=0、seed=None。Supervisor 没有输入 token 总长检查；最小验证必须按实际 RWKV 模板计数，使输入加输出预算在 16384 内。不能以字符数或中转报告的 prompt_tokens 替代本地计数。

health 仅 GET `/models`，验证两个 alias 同时存在；runtime doctor 存储 Supervisor settings/health，未在 SupervisorAPISettings 内绑定 model SHA 或 zero State。新的实验身份须引用同一现有服务的上传源码清单、模型 manifest / runtime safetensors SHA、tokenizer / generation config / launcher SHA、实际 served alias 和 zero-only 启动状态。原始 pth 的 source_weight_sha256 与运行时 safetensors SHA 应继续区分。

最小接入验收应先把已有生产构造函数生成的请求绑定字节及 SHA，检查真实模板/token 数，再使用同一现有服务参数进行小规模兼容验证；必须包含完整 GoalPlanPatch 和 StageReview 的本地类型/语义验证、finish_reason / token 使用、至少一次 Planner 后续修订和同实例跨请求隔离。最小 `{"ok":true}` 只验证格式，不证明角色协议或完整题集能力。变更 Supervisor 模型/模板/格式后需另立冻结身份，两遍基线一致；不应续用原中转 A 臂与新本地 B 臂直接比较。

## 可复核路径和 SHA

全部 CPU 输出 JSON 和 stderr、指定服务 journal 与作者脚本 SHA 由旁边 `READONLY_CONNECTION_AUDIT_SHA256SUMS` 绑定。JSON 中包含异常 stack；原 probe 响应未改写，未把模型 reasoning 原文加入本报告。主要源码 SHA：

- 本地 `rwkv_lh/supervisor_openai.py`：`5ee0e8580b0fb77fd6a6ed95c04b9044034ada7c3c4450c94681ad47c87252e3`
- 本地 `rwkv_lh/runtime/role_config.py`：`a75c606b3aa8548103cef534b240a9356c8d7026880e73a62367df0aed128ea3`
- 服务器 engine `vllm/tokenizers/rwkv.py`：`3bfbc1b7e578ffa8d6236ba0a6cf5b8ee0f46c1f1eace89922a1638c4d26deb4`
- 服务器 engine `vllm/tokenizers/rwkv_defaults.py`：`eb0e3e8f7269e63e04b32024bd64c565c430a43f5428d256fc22cb82b43ca0de`
- 服务器 engine `vllm/v1/worker/gpu/model_states/rwkv.py`：`ccf05d15ef481408bdeb4a175ed2efa937fec89720edeb24bd6a9a73ee73e0fa`
- 模型 generation_config.json：`f9312b9ad932e8ddfb913200a3d9688f718461a59f87feebba5ab4e48dedffae`
- 模型 tokenizer_config.json：`401caa50542469e88e5ace67fa20c1d78cefca5fbd4cf53d4df2de1762acca5c`

审计开始时 launcher SHA `810182f3cce9f18a9b55ad928126c7a08bb88dfa7b108a302073c7e7c733cf21`。主代理之后登记仅添加 log-error-stack 的新 SHA `fea02e5468e0542ff331eae23422361ce4cb2b2a6831f38f53a4aadb3d6cc480`；本报告没有把旧 launcher SHA 当作这一变更后的现状。
