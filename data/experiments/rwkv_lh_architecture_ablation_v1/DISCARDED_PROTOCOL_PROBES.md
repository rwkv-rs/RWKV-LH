# Discarded protocol probes

`g1i_chat_message_tool_dialog_probe_run1.json` 不进入线上 G1i 增量协议的质量结论。该运行让
`/chat/completions` 的默认 chat template 自行渲染角色；服务没有生成所需的 `Assistant: ```json`
前缀。它只证明当前默认 chat template 未对齐线上协议。

用户进一步明确：线上协议在同一 RWKV state 上逐块追加。第一次 user 内容是任务；后续 user 内容是
`Function output: ...`，每次生成前显式追加 `Assistant: ```json`。因此
`g1i_online_tool_dialog_format_comparison_run1.json` 的完整前缀重放是缺少 state handle 时的等价模拟，
可用于格式正确性比较；它不能证明 recurrent-state 复用的时延或状态一致性。

`vllm_rwkv_native_tool_parser_v2_run1.json` 的三个 native-chat 变体不进入 parser 结论。请求设置了
`thinking_token_budget=0`，但服务没有配置 reasoning parser，因此 native 请求在生成前统一 HTTP 400。
修正后使用新的 run 编号复测。
