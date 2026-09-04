# vLLM-RWKV 工具并发验证协议

日期：2026-09-01（Asia/Shanghai）

## 目标

验证本地 `vllm-rwkv` 的 RWKV 原生工具解析、XGrammar 约束和流式输出在高并发下不会重复发射工具调用，也不会跨请求复用响应或工具调用 ID。

## 固定实现与数据

- 引擎基线：`/home/chase/GitHub/vllm-rwkv`，HEAD `4b5cebdc28f24b24efae20e6e8e64420abc2eef3` 加本次未提交工作树修改。
- 权重：`/home/chase/models/rwkv7-g1-st/rwkv7-g1j-1.5b-20260831-ctx16384`。
- 测试脚本：`/home/chase/GitHub/RWKV-LH/temp/verify_live_vllm_rwkv_tools_20260901.py`。
- 请求数据由脚本确定性生成：单调用参数为 `city-{0..255}`；并行流式参数固定为 `Paris` 与 `Berlin`。
- 解码参数：`temperature=0.0`，工具用例 `max_tokens=96`。

## 固定指标与阈值

本实验不是架构质量消融，不使用主观相似度。协议正确性使用精确相等与集合基数计算：

1. 256 个并发单调用请求必须全部恰好产生 1 个工具调用，阈值 `256/256 = 1.0`。
2. 响应 ID 唯一率必须为 `256/256 = 1.0`。
3. 单调用工具 ID 唯一率必须为 `256/256 = 1.0`。
4. 64 个并发流式请求各产生 2 个调用；128 个调用必须全部只发射一次，阈值 `128/128 = 1.0`。
5. 流式工具 ID 唯一率必须为 `128/128 = 1.0`。
6. 强制工具调用的内容泄漏必须为 0。
7. `parallel_tool_calls=false` 必须最多返回 1 个调用。

`city-N` 参数原样保留率单独记录为模型语义指标，不作为并发重复缺陷的通过条件，也不得在运行后改变其精确字符串比较口径。

## 覆盖场景

- 普通生成（覆盖 RWKV rapid-sampling/CUDA Graph 路径的可运行性）。
- `required` 与具名函数选择。
- 单调用与多调用。
- 非流式与流式。
- strict 与 non-strict 工具 schema。
- `parallel_tool_calls=true/false`。
- eager 与非 eager CUDA Graph 服务。
- 分块解析、非法 JSON、未知/错误具名工具和重复 `finish_streaming()` 的 CPU 回归。
