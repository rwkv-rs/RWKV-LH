# Round38 B27 参数语义 canary

## 结果

- Strict：FAIL
- External：FAIL
- Agent：blocked
- workspace 未被错误标记为完成

## 因果链

RWKV 本次为 `replace_text` 省略 count，因此使用协议声明的默认值 1。Harness 原样替换一次，没有静默修改显式参数。文件最终仍包含两个 `protocol=v1` occurrence（其中一个位于 `fallback_protocol=v1`），外部验收正确失败。

后续 read_file 观察到真实剩余内容。Goal evidence 未收口，obligation replan 两次返回非 canonical Task batch，Agent blocked。与 Round36 的 Agent completed / External FAIL 相比，错误状态没有被假阳性放行。

## 结论

Round38 不提高本题分数，但消除了执行层改写 RWKV 参数的接口缺陷：显式非法 count fail-closed，省略 count 使用固定默认 1。要完成“替换所有 occurrence”，RWKV 必须根据真实观察选择合法 count 或其它策略；Controller/Harness 不猜测 `-1` 的含义。
