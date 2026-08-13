# Round38 预注册协议：禁止 Harness 静默重解释参数

## 触发证据

Round35/36 的 B27 中，RWKV 为 `replace_text` 返回 `count=-1`。G1i 描述写着 positive integer，但生成的 JSON Schema 只有 `type=integer`，`validate_action_contract` 也未检查正数。执行端再运行：

```python
expected = max(1, int(arguments.get("count", 1)))
```

因此 RWKV 的 `-1` 被静默改成 `1`，只替换一个 occurrence。该行为既造成错误结果，也违反“不得对 RWKV action 参数增删改查/重解释”的边界。

## 单一变更

- `replace_text.count` 的 authoritative schema 改为 `integer, minimum=1`。
- model action contract validation 在执行前拒绝 bool、非 integer 和 `<1`。
- handler 不再使用 `max` 或 `int` coercion；缺省仍为协议定义的 `1`，显式值原样使用。
- 即使绕过 model boundary 直接调用 Harness handler，非法 count 也返回失败，不产生副作用。

## 明确禁止

- 不把 `-1` 猜成“全部替换”，也不把它夹到 1。
- 不根据 Task 文本替 RWKV选择正确 count。
- 不新增格式别名，不修改文件内容或最终回答来通过 B27。

## 固定验证

1. G1i tool schema 的 `count.minimum == 1`。
2. validate_action_contract 对 -1、0、bool、string fail-closed。
3. direct Harness execute 非法 count 返回失败且文件字节不变。
4. valid count=2 原样替换两次；省略 count 原样使用默认 1。
5. 全量 pytest、LH-Control 30/30、E2E-90 validate-only 90/90。
6. B27 canary 只观察 RWKV 是否根据明确 schema 选择合法参数；若仍非法则应阻塞而不是假阳性。

## 成功判据

- 执行层不再静默改变 RWKV 参数语义。
- 非法输入不会产生 workspace side effect。
- B27 不再以“提交 -1、实际执行 1”的链路完成。
