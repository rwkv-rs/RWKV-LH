# 强 Planner 输入—输出消融 V2 分析

## 完整性与边界

- 结果：`run_v2/RESULT.json`
- 文件 SHA256：`c89123a806f7c6a72e2f011076425c8d6fbe79c570bd7c21bea592c800743313`
- 5 个公开任务 × 3 臂 = 15 个独立原始响应；15/15 HTTP 200，15/15 为单个 JSON 对象，15/15 通过对应 strict JSON Schema。
- 15/15 完整输出覆盖请求中词法识别的路径；15/15 图的节点 ID、依赖存在性与无环性合法；15/15 未出现具体 Harness operation 名称。
- 未读取隐藏验收，未调用 RWKV，未使用 GPU，强模型原始 assistant content 保存在各例 `RAW_PROVIDER_OUTPUT.txt` 中且未修改。

## 输入与输出统计

| 输入臂 | 平均请求 token | system prompt token | 平均延迟（ms） | 平均输出 bytes | 当前生产语义接受 |
|---|---:|---:|---:|---:|---:|
| A 当前长提示词 + typed DSL | 3226 | 1098 | 8924.2 | 5720.4 | 0/5 |
| B 精简提示词 + typed DSL | 2237 | 134 | 13110.0 | 7169.2 | 0/5 |
| C 精简提示词 + 精简契约 | 1683 | 134 | 7966.4 | 3581.6 | 不适用（候选新契约） |

C 相对 A 将平均请求 token 减少约 47.8%，平均输出 bytes 减少约 37.4%；本样本只作描述性比较，不声称延迟显著性。

## A/B 的 10 个生产拒绝

- 词法 typed-path 覆盖：3 例。模型完整输出已经理解路径，但本地规则要求 assertion 中出现裸路径；例如模型正确使用 `inventory/storage.py`，校验器却要求请求字面量 `storage.py`。
- obligation 交叉引用：5 例。复杂 schema 让模型把多个断言放进一个 obligation，却让节点引用预想的多个 obligation ID；strict Schema 无法表达同响应内部的动态外键。
- assertion DSL 字段语义：2 例（空 target_path、非 JSON Pointer）。两例 JSON 与 Schema 都合法，只是二次 DSL 规则拒绝。

因此“强模型不按 JSON”是假设不成立。正式配置必须显式发送 `reasoning_effort="none"`；在 V1 误省略该字段时，上游曾在 strict JSON 响应前插入 `<think>`，V1 已标记 INVALID。

## C 的结构规律

- 5/5 obligation ID 引用完整：无未知引用、无未绑定 obligation。
- 5/5 生成了语义正确的调查—修改—验证图；所有 mutation 都能沿依赖链到达后续 verify。
- 当前“必须直接依赖且 verify.read_roots 逐根完全重叠”只通过 2/5。失败例仍有明确验证阶段：例如 Web 项目验证节点运行 `verify_project.py`，网络项目以多级修改后统一验证。问题是本地规则只接受直接边和精确 root，而不接受传递依赖或项目级验证。
- `write_roots.maxItems=2` 导致 2/5 输出把多个文件挤进一个字符串（如 `"styles.css','app.js','README.md"` 或 `"styles.css,"`）。这是 Schema 容量与中型项目不匹配，不是路径理解失败。

## 结论

生产问题位于 Planner 契约编译层：typed-assertion DSL、动态外键和最多两个写根把强模型自然、合法的计划拒绝或扭曲。应保留 strict JSON 参数、不可变 request 尾布局和安全权限边界；删除 Planner 手写 typed DSL、evidence freshness/source preference/action budget 等机械字段。Controller 根据阶段 kind、effect、义务和依赖编译这些字段，并把上游 mutation 写根传播到后续 verify 的读范围。这样不替代 Planner 的目标分解，也不替代 2.9B Selector 或 13.3B Executor。

