# Round36 `tool + args` 五题定向分析

## 结果

- Strict：`3/5`
- PASS：B01、B02、B11
- B12：External PASS、Agent blocked
- B22：Agent completed、External FAIL

## 因果结论

### B01、B02、B11

三题的主要产物和最后读取动作都正确。最后的 `tool + args` 响应分别以 `tool_args_alias_to_canonical` 转为唯一内部 `name + arguments`，未发生协议重试，三题均 Strict PASS。转换事件保留 raw/normalized payload 和 digest，`controller_semantic_fields_generated=false`。

### B12

Round36 成功转换了一次 `tool=read_json + args`，但后续冗余读取动作又给 `read_json` 添加了不属于其 schema 的 `start_char`。Harness action contract 两次拒绝该参数并阻塞。格式层没有删除 `start_char`，因此行为符合 fail-closed 边界。实际 `stats.json` 内容正确，问题已从表示接入转为工具 schema 混淆/冗余验证 Task。

### B22

Round36 成功转换最后的 `tool=read_file + args`，使 Agent 能继续完成；但 RWKV 早先写出的 `TASKS.md` 是普通项目符号：

```markdown
# Tasks
- inspect
- repair
- verify
```

用户要求的是 unchecked Markdown items，实际应包含 `- [ ]`。转换层没有改正文，External 正确失败。RWKV 的 Task postcondition 和 Goal commit 仍过度声明，产生假阳性。该题证明格式转换只提高协议可达性，不保证内容正确，也不承担正确性筛选。

## 结论

`tool + args` 是高频真实接入格式，定向 3 题被直接救回；另外两题的语义/工具参数错误仍原样暴露。Round36 达到了纯格式层目标，但必须跑完整 Basic30 才能量化净结果，且不能据此上传。
