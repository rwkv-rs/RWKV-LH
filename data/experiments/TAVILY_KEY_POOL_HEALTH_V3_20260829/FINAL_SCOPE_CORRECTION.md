# V3 最终范围纠正：实际 key pool 为 17

登记时间：2026-08-29；本文件不触发任何新外部调用。

## 根因与证据

V3 的 29-key 输入假设来自一次临时只读盘点命令。该命令在 shell 内把 Python 正则错误写成了匹配字面反斜杠/字母 `s` 的形式，导致 Tavily key 自身包含的 `s` 被误当作分隔符。使用项目正式实现同一正则 `r"[,;\s]+"`、Python 标准库直接读取和审计器三条路径复核后，ignored `.env.local` 的唯一 Tavily key 数均为 17。

- 既有 V2 正式审计：17/17 usable，0 permanent unavailable，0 temporary/uncertain，secret-free，passed。
- V3 R1：实际调用同一 17 枚，17/17 usable；仅因错误预注册要求 29 而 `passed=false`。
- V3 R2：清除继承环境后仍为同一 17 枚，17/17 usable；再次证明 `.env.local` 与进程配置没有额外 12 枚。
- V3 R3 的所有尝试均在计数前置条件处 fail closed，零外部调用、未创建 R3 结果目录。

因此 V3 的“29-key 完整池”问题本身范围无效，不再重试或改变门槛。当前有效产品结论继续引用 V2：`.env.local` 中 17 枚均可用，没有不可用 key 需要删除；真实值从未进入报告或日志。

