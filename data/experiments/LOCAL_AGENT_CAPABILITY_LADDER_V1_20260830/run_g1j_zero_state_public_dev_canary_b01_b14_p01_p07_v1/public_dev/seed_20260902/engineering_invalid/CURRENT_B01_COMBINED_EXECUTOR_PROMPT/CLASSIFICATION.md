# B01 工程无效运行分类

- 分类：`engineering_invalid`
- 用例：`PUBLIC-CANARY-B01-S20260902`
- 状态：人工中止；数据库中的 `running` 属于中止后的陈旧状态，不代表能力结果。
- 基线有效性：无效，不得计入 zero-State Agent 能力基线或后续 StateTune 对照。
- 数据处置：原始工作区与 SQLite 状态完整迁移至本目录，没有删除，仍可复核。

## 根因

该运行的 Executor 输入错误地把两套续写协议拼接在同一个请求中：先出现旧式
`Assistant: ```json`，随后又出现 `ExecutorArgsPromptV1` 与
`**Tool Call:** → ```json`。因此连续拒绝来自工程侧输入构造错误，不能归因于模型能力、
token 预算或中转站稳定性。

中止前的可复核计数为：模型接受 57 次、模型拒绝 115 次、协议拒绝 128 次、已执行动作
57 次。拒绝链已经造成异常上下文膨胀，所以即便继续运行也不再具有基线效度。

## 整改后唯一协议

当前 G1J 的所有文本生成环节只允许一套输入结尾：

````text
<RolePromptV1 JSON>

**Tool Call:**

```json
````

旧式 `Assistant: ```json` 不得进入当前 G1J 产品路径。Selector 只做 logits/head
分类，不生成文本；GPT Planner 与 Claude Stage Checker 只使用各自 API 的
`json_object` 传输约束，不构成第二套 G1J 续写协议。

## 后续运行

修复后的 B01 必须重新从固定路径
`public_dev/seed_20260902/cases/PUBLIC-CANARY-B01-S20260902` 开始；本目录只保留为工程
故障证据。
