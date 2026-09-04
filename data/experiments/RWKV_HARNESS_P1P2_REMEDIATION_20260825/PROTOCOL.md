# 主动 Harness P1/P2 审查整改协议

状态：`REVIEW_FROZEN`。输入为用户提供的静态审查清单：3 个 P1、5 个 P2；整改期间不得把任一项降级为
“模型问题”，不得用 case 特判修复，也不得启动 R9 后续正式实验。

日期：2026-08-25（Asia/Shanghai）

固定整改项：

1. proactive 终态写入必须校验 worker、单调 lease generation 和未过期 lease；
2. contract result 截断后不得保留完整证据语义；
3. contract-graph v2 必须进入所有恢复/实验架构判定；
4. progressive 已披露工具参数重试必须重新执行上下文预算检查；
5. 已提交 retrieval route snapshot 优先恢复，缺失时禁止 provider 重放；
6. text template 必须保持数量、非重叠匹配，并先形成排序后的期望序列；
7. 空集合 minimum/maximum 不得抛出未捕获异常；
8. 所有 stream HTTP 响应路径必须关闭 response。

固定完成门槛：每项都有失败窗口回归；相关定向测试全过；全量 pytest、compileall、JSON/摘要和
`git diff --check` 全过。R9、route120、Full90 不属于本轮整改执行范围。
