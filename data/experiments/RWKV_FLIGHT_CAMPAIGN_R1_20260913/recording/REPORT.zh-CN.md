# 执行归属与提供方用量记录整改

本轮没有新模型任务，不重算上一轮评分。历史有效接管仍 0/1 合格、1 部分满足，completed 0、一次命令修改两个文件，预算终止。四次 RWKV 续修仍全无交付。只整改工程记录，不报模型质量收益。

确认两个共享链路问题：Controller 最终提交来源固定 RWKV，且 Goal 的自愿完成校验只接受该来源；统一 capture_diagnostic_run 对缺失 token ID 调用 len(None)，不能直接导入 strong 的真实结果。原接管的人工外部账没有漏记，但通用捕获入口不能正常处理。

修复后，显式 execution_authority 从共享入口传入 Controller，四处直接 Final 来源以及原始输出失败来源跟随实际执行主体。默认仍为 RWKV；strong 完成必须有显式接管授权和真实 Final 决策，不能只换标签就通过。保留原 Goal 默认策略字节与摘要，不为本次支持改写已有不可变目标；显式接管是额外的运行授权，非隐式重解释旧 State。

统一捕获优先用真实 token ID；缺失时要求运行目录内的原始提供方回执，绑定响应身份、模型、原文与停止原因。提供方不返回 response ID 时，必须有本地 call_id 对应的真实 wire 主输入，且与该生成的 State 文本唯一对应；无法核验则拒绝，不猜 token，不记零。提供方实际 prompt/completion 统计含 reasoning 和失败消耗，并记录 provider_usage_calls，不能当作获得了强模型精确 token ID。本地 RWKV tokenizer 不用于冒充 strong 计费量。

回归：修正夹具后的旧冻结源码 8 failed；完成授权额外红灯1，缺失response ID回执路径红灯1（反例通过）。最终相关117 passed，全量1618 passed/零跳过。初始夹具把工具字典当字符串、并行 pytest 默认工件目录冲突以及只改标签尚未打通完成校验的失败候选均保留，未伪装成模型或正式修复收益。后续测试使用独立 basetemp。

真实轨迹重放核验：原strong两次准确捕获31883输入/3217输出，含首次length；四个native续修的调用/token/协议拒绝计数保持原值。没有发起新模型请求，没有改动历史原文或评分。完整原始命令台账依然含父历史；调用方统计新增工具错误时仍须按 continuation.historical_actions 切分，不能误计为本轮错误。

范围限于共享直接执行入口及外部捕获；strong chat 传输仍是实验适配，公共编程 CLI 未新增自动接管决策。未增加规划/审核角色，未补写业务参数或答案。下一轮额外只读 bug 检查与独立并发已在本轮最终源码上冻结，结果另报。

owner 原五处修改保留，Controller 仅暂存 HEAD 加本轮补丁；原始红灯日志尾空格保留。无 GitHub、训练、新 datasets。
