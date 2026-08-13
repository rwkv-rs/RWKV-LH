# Round39 预注册协议：RWKV 已选工具的单 schema 参数纠正

## 触发证据

Round36 Basic30 中仍有 7 次 action argument rejection，常见为：

- RWKV 已明确选择 `write_json`，但混入 `write_file` 的 `overwrite/create_parents`；
- 已选择 `read_file/read_json`，但混入另一个读取/evidence 工具的 `end_char/start_char/source_label`；
- 已选择 `copy_file`，但参数不完整。

当前第二次 correction 仍把全部 15 个工具 schema 重新展示给 RWKV，参数混合通常原样重复。Round35 已证明弱模型会复制邻近的内部/schema 字段。

## 单一结构变更

保持第一次 action commit 不变：RWKV看到完整注册工具目录，并在一个显式 function-call envelope 中自行选择工具名和参数。

若且仅若：

1. 第一次 envelope 已被格式层完整解析；
2. 工具名是已注册工具；
3. 失败仅来自该工具的 Harness argument contract；

第二次请求固定为 RWKV 第一次选择的同一个工具，只展示该单一工具定义，并要求 RWKV重新返回完整参数。`expected_name` 必须等于第一次 RWKV 输出的 name；第二次不得切换工具。

若第一次没有唯一工具 identity、JSON 不完整或工具名未知，沿用原 fail-closed 路径，不由 Controller 猜工具。

## 明确禁止

- Controller 不从 Task title/description 选择工具。
- 不删除额外参数，不补 required 参数，不从依赖自动复制参数。
- 不把 write_json 的 write_file 参数过滤掉使其通过。
- 不改变第一次已合法 action，不增加额外“优化”调用。
- 不根据外部验收或答案决定是否纠正。
- Round39 不改格式别名、规划、Task/Goal pass 判定。

## 固定验证

1. 第一次工具与参数合法：仍只请求一次。
2. 第一次已选合法工具但参数非法：第二次 system tool list 恰好一个，name 与第一次相同，不包含其它工具 schema或 rejected JSON。
3. 第二次尝试切换 name：fail-closed。
4. 第一次 JSON/identity 无法解析：不生成 selected name。
5. 全量 pytest、LH-Control 30/30、E2E-90 validate-only 90/90。
6. 定向 canary：B14、B15、B21、B25、B30；逐题报告是否参数混合消失、External/Strict/FP/FN。

## 成功判据

- 已选工具的 correction 不再受其它工具 schema 干扰。
- 所有最终参数仍逐字段来自 RWKV，Controller semantic fields generated=false。
- invalid/missing arguments 仍由唯一 Harness contract 验证。
