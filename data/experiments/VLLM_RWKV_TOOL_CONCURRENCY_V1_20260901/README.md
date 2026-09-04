# vLLM-RWKV 工具并发整改与验证记录

## 结论

本次验证确认：RWKV 工具协议的重复发射和跨请求 ID 冲突在覆盖的 eager、CUDA Graph、单/并行、流式/非流式场景中均未复现。预登记的工具协议指标全部达到 `1.0`。但不能据此宣称模型语义推理已经完美：合成参数 `city-N` 的原样保留率在最终 CUDA Graph 高压运行中为 `98/256 = 0.382812`。

## 根因与整改

原 RWKV 解析器在每个流式增量上重新扫描累计文本，并由独立状态数组判断是否已经发送；在并发、多工具和结束重放组合下，职责分散且难以证明只发射一次。整改将 RWKV 格式迁移到通用声明式 `ParserEngine`：

1. 新增通用 OpenAI JSON envelope 模式，在 closing fence 到达后只解析和校验一次，并把 slot 标记为 finalized。
2. 工具调用 ID 绑定到请求解析器的 slot/stream state；每个 slot 只创建一次，不依赖重新扫描全文。
3. 在解析层统一执行具名工具校验和 `parallel_tool_calls=false` 的首调用封锁。
4. RWKV 解析器缩减为格式声明和模型特定的原生前缀处理，不再维护第二套重复状态机。
5. XGrammar 对 RWKV strict schema、non-strict object 契约、具名/required 选择和单调用约束统一生成 structural tag。
6. 新增通用的 pre-tokenization parser hook。RWKV required/具名选择使用模型模板原生 `fake_think`，避免 `<think>` 推理耗尽工具输出预算；显式 request-level 配置仍可覆盖。
7. `fake_think` 模式生成的补全前缀 `>\n` 在 RWKV parser 中按增量安全剥离，避免泄漏到 content。

## 上下游与影响范围

- 上游：OpenAI chat request、tool choice、chat template kwargs、strict/non-strict JSON schema。
- 核心：OnlineRenderer 预分词钩子、Parser/ToolParser 适配、ParserEngine slot 生命周期、RWKV 格式配置、XGrammar structural tags。
- 下游：非流式 `tool_calls`、SSE 增量、finish reason、调用 ID、`parallel_tool_calls` 行为。
- RWKV 状态传递和 FlashRWKV2 recurrent state 没有被辅助模型或额外模型调用替代；工具约束存在时走 grammar-aware sampler，无约束普通生成走 RWKV rapid-sampling。

## GPU 验证

权重与硬件摘要见 `manifest.json`。生产路径使用：

```text
--dtype float16
--max-model-len 512
--max-num-seqs 16
--gpu-memory-utilization 0.32
--cudagraph-capture-sizes 1 2 4 8 16
```

默认 CUDA Graph 捕获规模会扩到 2048，在当前另有用户 GPU 进程的环境下额外占用约 4.9 GiB并使 KV cache 预算为负。显式限定实际服务批次后，graph 实际占用约 0.07 GiB，服务正常启动，保留约 1.57 GiB / 114,688 tokens KV cache。该配置问题属于部署容量规划，不是工具解析逻辑错误。

CUDA Graph 高压结果：

- 256 个 required 单调用：256 个调用，全部恰好一次。
- 256 个响应 ID：全部唯一。
- 256 个单调用工具 ID：全部唯一。
- 256 个请求的编号身份：全部保持，无跨请求参数串线；模型只会把本请求的 `city-N` 归一化为同一个 `N`。
- 64 个并发并行流式请求：128 个调用，全部只发射一次且 ID 全唯一。
- required/具名、strict/non-strict、`parallel_tool_calls=false`：通过。
- 总耗时：9.396 秒。

## 回归

- 相关单元测试：242 passed，0 failed。
- 此前扩展相关 parser/tool/renderer 回归：3926 passed。
- smoke 回归：40 passed。
- changed-file pre-commit：ruff、format、mypy、SPDX 等全部通过。
- `git diff --check`：通过。

## 已知限制与风险

1. `city-N` 精确字符串在最终 CUDA Graph 运行中只有 98/256 保留；其余 158 项均是模型把本请求的 `city-N` 归一化为同一个 `N`，请求身份保持率为 256/256。XGrammar 保证 JSON/schema，不保证模型复制任意字符串的语义精度。
2. 普通生成 smoke 可运行并进入 rapid-sampling graph，但 16 token 限制下没有遵守“只输出 OK”的合成指令。这同样属于当前 1.5B 权重的指令遵循能力。
3. structural output 存在 grammar bitmask 时，RWKV rapid-sampling 按设计返回 fallback，随后由 vLLM 通用 sampler 应用 grammar；因此工具高压覆盖的是 RWKV 模型/CUDA Graph 加 grammar-aware sampling，而非 FlashRWKV2 rapid-sampling 内核本身。
4. 工作树尚未提交；最终集成前仍应在目标部署环境运行完整仓库测试和长期 soak。

详细门槛见 `PREREGISTRATION.md`，结构化结果见 `results.json`，来源和哈希见 `manifest.json`。
