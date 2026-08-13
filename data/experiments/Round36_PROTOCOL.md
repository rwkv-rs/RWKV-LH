# Round36 预注册协议：`tool + args` 纯格式转换

## 触发证据

Round35 Basic30 的冻结 `model_trace.json` 中，`tool_action_commit` 已解析对象的顶层形状统计为：

- `tool + arguments`：113 次
- `tool + args`：41 次
- `name + arguments`：16 次
- 其他含额外字段的形状：9 次

`tool + args` 的 41 次对象中，`tool` 都是显式非空工具名，`args` 都是完整 JSON object；这与已接入的 `tool + arguments` 只差参数容器的常见键名。B01、B02、B11、B12、B22 都在已正确完成主要产物后，因该形状的最终读取/验证动作被拒而阻塞。

数据来源为 `data/experiments/Round35_basic30_compact_phase/cases/*/model_trace.json`。30 个 trace 按路径排序、逐文件 sha256 后的集合摘要为 `95d8dce6ad1eeb7aa71d7bcf9da60d21a6644c96a4d8f42cbaba0ae4f8ed3600`。本轮开始后不新增别名。

## 单一变更

在 G1i wire-format converter 的闭集增加一种精确表示：

```json
{"tool": "read_file", "args": {"path": "result.txt"}}
```

转换为：

```json
{"name": "read_file", "arguments": {"path": "result.txt"}}
```

只重命名两个协议 key；工具名与 args object 的全部 key、value、类型、嵌套结构保持不变。转换后仍由唯一 canonical G1i validator 和 Harness action contract 校验。

## 明确禁止

- 不接受同时存在 `args` 与 `arguments` 的对象。
- 不删除 `reasoning`、`description`、`id`、`execution_capsule`、`next_cursor` 或任何其他额外字段。
- 不把 `write_json` 的 `overwrite/create_parents` 删除掉。
- 不补缺失工具参数，不改工具名，不修路径、数值、文本或答案。
- 不根据 active Task、外部验收或标准答案决定转换。
- Round36 不改 prompt、Task planning、memory capsule、Goal evidence 或 recovery。

## 固定验证

1. 单元测试：exact `tool + args` 只改变两个键，嵌套 args object 保持对象和值相同。
2. 单元测试：args 为 string/list/null 仍由 canonical validator 拒绝，不做类型 coercion。
3. 单元测试：混合 `args + arguments`、额外字段、空工具名继续 fail-closed。
4. 审计保存 raw/normalized payload、digest、转换名和 `controller_semantic_fields_generated=false`。
5. 全量 pytest、LH-Control 30/30、E2E-90 validate-only 90/90。
6. 真实定向 replay：B01、B02、B11、B12、B22；报告 Strict、External、FP/FN、请求数与是否仍存在语义错误。
7. 若定向因采样产生新形状，不在本轮追增 converter。

## 成功判据

- exact `tool + args` 无需协议重试即可进入唯一内部格式。
- 所有内容/参数/额外字段错误仍被下游原样拒绝。
- 离线回归无退化。
- 本轮只证明接入格式完整性；是否提高 Strict 需由真实定向结果另行判断。
