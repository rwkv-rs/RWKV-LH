# JSON mode HTTP 500 的已证实导入失败与支持范围

这是新证据的独立后续报告，`READONLY_CONNECTION_AUDIT.zh-CN.md` 和其清单保持不变。本次只读本地证据与远端对应源码，不安装依赖、不改服务/源码/配置、不生成、不加载模型，不在服务器运行 Git。

本次已证实的首错为缺少 `lmformatenforcer`，发生于请求采样参数校验。不能把此前发现的 Xgrammar 缺失改称为这次 traceback 中的首错。原格式重放事件 `chatcmpl-bc8955fb756cbb60`，APIServer PID 1486276，时间 2026-09-07 13:10:43 +08:00；HTTP 500，响应 message 为空，耗时 0.132 秒。`OUTPUT_INSPECTION_JSON_ERROR_STACK.json` 的 max_tokens 仍为 1800；此请求没有生成 token。

## 因果链

1. Supervisor 原请求传 `response_format={"type":"json_object"}`；`vllm/entrypoints/openai/engine/protocol.py:179` 将其映射成 StructuredOutputsParams(json_object=True)。因此它触发服务 grammar 链路，而不是仅要求客户端输出后 json.loads。
2. Chat serving 调用 `AsyncLLM.generate`，随后 `async_llm.py:352` 在 add_request 中调用 input_processor.process_inputs。`input_processor.py:271` 调 `_validate_params`，第 110 行调 SamplingParams.verify。
3. `sampling_params.py:837` 进入 `_validate_structured_outputs`。如果 self.structured_outputs 为 None，该方法第 997 行提前返回，解释了普通请求没有走这个失败点。
4. 有约束时，该方法第 1069–1080 行在选择具体 backend **之前**依次导入 guidance、lm-format-enforcer、outlines、xgrammar 的校验函数。此时尚未执行第 1082 行之后的 backend 分支，即使设置显式 xgrammar，也不会跳过前面的 LMFE 模块导入。
5. `backend_lm_format_enforcer.py:44–45` 定义 LMFormatEnforcerGrammar 时，字段注解 `token_enforcer: lmformatenforcer.TokenEnforcer` 被 Python 3.12 当场求值。该模块没有 `from __future__ import annotations`，这个注解也没有字符串化。第 26 行的 LazyLoader 因属性访问而调用 `import_utils.py:383 -> 367 importlib.import_module`，抛 `ModuleNotFoundError: No module named 'lmformatenforcer'`。
6. `async_llm.py:623–635` 将这一意外异常包装成不带 message 的 EngineGenerateError。该请求尚未到 `async_llm.py:416–421` 的 `_add_request` / engine_core.add_request_async，因此没有提交 EngineCore，不涉及本次请求的 RWKV prefill、采样或 State 执行。
7. `server_utils.py:365` 的 engine_error_handler 在启用 log_error_stack 后记录完整 cause chain；向 HTTP 转换的是外层 EngineGenerateError，故用户最初看到空 message 500。此前只检查通用 exception_handler 无法定位此次包装后的实际分支，新 traceback 补足了这点。

## 一个依赖与 V2 的边界

当前 `StructuredOutputsConfig.backend` 缺省为 auto（`vllm/config/structured_outputs.py:21`），launcher 没有选择其他 backend。单独补上 lmformatenforcer 至多解除已记录的第一个导入阻塞，不能证明后续成功：

- 此前 tokenizer-only 诊断已证实同 engine Python 环境 `import xgrammar` 不存在。当前 auto 分支首先运行 validate_xgrammar_grammar；单纯 json_object=True 不会在该校验函数里主动加载 Xgrammar，然后将 backend 选成 xgrammar。后续 grammar_init 第 133 行会构造 XgrammarBackend，其 TokenizerInfo.from_huggingface / GrammarCompiler 需要真实 Xgrammar 模块。
- 现有 RWKVTokenizer 不是 Hugging Face fast tokenizer。由于依赖尚不可导入，此前没有执行 TokenizerInfo.from_huggingface，也没有证据证明或否定它对该 RWKV 词表的实际兼容性。不能通过 tokenizer 可构造反推 grammar 编译、token mask 与停止边界都正确。
- auto 只对 validate_xgrammar_grammar 的 ValueError 做后备路由；ModuleNotFoundError 不属于这个捕获范围。当前请求也不允许任意通过内部 `_backend` 字段覆盖服务固定配置。
- 安装行为可能引入怎样的传递依赖、版本和二进制兼容变化，本审计没有执行或假设。没有证据支持“只补一个依赖就够”；完整依赖/选定 backend/tokenizer/实际生成链必须另行验证。

也不能把现状概括成“V2 完全不支持 structured outputs”：实际 `_build_profile.json` 明确声明 structured_outputs；InputProcessor 只在受限 profile 未声明此能力时拒绝，本次已经越过该检查。当前 V2 `vllm/v1/worker/gpu/model_runner.py:374` 在最后一个非 pooling rank 建立 StructuredOutputsWorker；第 1180–1188 行在 sampler 前给 logits 应用 grammar bitmask。`worker/gpu/structured_outputs.py` 包含 mask 复制、请求/行映射、Triton mask kernel。`v1/structured_output/__init__.py:114–174` 有 backend 初始化与 grammar 编译调用链。这些代码证明存在实现路径和 capability 声明；不等于当前环境依赖完整，更不等于本轮 RWKV 上已经验证其运行正确。本次异常发生在它们运行之前。

## 证据绑定

- `JSON_ERROR_STACK_JOURNAL.txt`：`a4b86889336f46006bce2595aa44a1179fba069a1420dc93cb5782167b2d3a3c`
- `OUTPUT_INSPECTION_JSON_ERROR_STACK.json`：`5c4b5ce2549a1ff5ef188715018bf7167dd4734da479b0337d70649770291e17`
- `STRUCTURED_OUTPUT_IMPORT_PATH_REMOTE_SOURCE_SHA256SUMS`：`8b18e231280d553f8854a539c2bc8323c4061fb367b6bd484238ace0af0aa94c`，绑定本次读取的远端完整源码文件，而非只绑定摘录。

此前 `XGRAMMAR_TOKENIZER_OFFLINE.json` 是另一个独立兼容诊断，其“缺 Xgrammar”结论继续有效，但不是此次实际 traceback 的第一异常。此次整改范围位于通用结构化输出依赖导入与部署能力声明之间，影响所有非空 structured_outputs 请求；没有用例、Planner 阶段或任务 ID 特判。
