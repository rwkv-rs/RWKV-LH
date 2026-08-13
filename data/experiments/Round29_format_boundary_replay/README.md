# Round29 格式归一化边界回放

日期：2026-08-13。normalizer：`transparent-protocol-boundary.v2`。

## 数据登记

- 来源：`data/experiments/Round22/cases/*/model_trace.json` 的冻结真实 RWKV 输出，共 90 个 case、579 个
  `tool_action` request。
- 来源版本：Round22；每个源文件的相对路径和 SHA-256 登记在
  `round22_tool_boundary_v2.json.source_files`。
- 用途：只验证常见工具调用外壳能否透明转换；不运行模型、Harness、verifier，也不读取或改变标准答案。
- 生成方式：
  `.venv/bin/python /home/chase/GitHub/RWKV-LH/temp/replay_round22_tool_boundary_v2.py`。
- 结果文件 SHA-256：`05d8e40a7d220a51d81397e402854c77815607796554c15d8a92bae17d418837`。

## 白名单设计

代码只登记四个外壳族：canonical call、flat name alias、single nested call、single `tool_calls`。具体历史拼写
共享同一个解包入口，不进入 Controller 业务逻辑。允许的操作只有：

1. 从唯一外壳中取出显式工具名；
2. 将显式平铺参数整体移动到 `arguments`；
3. 将 JSON 字符串形式的 `arguments` 解码为对象。

工具名不得做字符串 coercion 或 trim；参数字段不得筛选、补全或改值；多调用、多个参数来源、额外协议字段和工具名冲突
全部 fail closed。Task graph 的冗余 edge 也只允许精确的 `source/target` 镜像，不能携带被转换层丢弃的描述语义。

实现上进一步把两项职责物理拆开：`convert_*_format_with_trace` 只搬运已登记外壳并记录 raw/converted payload；
`validate_canonical_*` 才检查项目唯一内部协议的 name、arguments、schema 和字段集合。格式转换器不会因为工具名为空、
schema 错误或参数不符合 action contract 而把它修成合法内容；这些输入在转换后仍由唯一内部协议拒绝。整个项目的 Controller、
Harness 和 TaskGraph 只接收 canonical 格式，不分别兼容多种模型输出。

## 全量回放结果

- 接受：`562/579`；拒绝：`17/579`。
- 接受后 name/arguments 与源字段不一致：`0`。
- Round23 已接受、v2 反而拒绝：`0`。
- 新增透明恢复：`10`，其中 `flat_action_envelope_to_canonical=9`，
  `flat_action_type_envelope_to_canonical=1`。

10 条新增恢复逐条来自：E2E-B10、E2E-B30、E2E-H15、E2E-H16、E2E-LH03、E2E-M02、E2E-M05、
E2E-M11、E2E-M17、E2E-M29。每一条都只有一个显式 action 名和一组平铺参数；转换后仍需通过所选 action 的真实
参数 contract。

剩余 17 条不是同类格式问题：

- 12 条显式工具名与已选择 action 不同（例如选择 `read_json` 却调用 `read_text/read_csv`，或调用
  `model_action`）；这是 RWKV 决策冲突，不能归一化为正确工具。
- 4 条混入第二参数来源或 Task/lifecycle 元数据；转换会产生歧义，继续拒绝。
- 1 条没有完整 JSON 对象；没有可透明恢复的输入，继续拒绝。

因此本层只消除共同的 wire-format 摩擦，不判断 action 是否正确，也不修改 RWKV 的最终答案。

## 改动后回归

- 完整 pytest：`317 passed in 31.36s`。
- LH-Control-30：`30/30`，见 `lh_control_30/`。
- E2E-90 validate-only：`90/90` catalog valid，见 `e2e90_validate/`。
- 真实 RWKV canary 尚未在本记录完成：转发 unit active，但服务器重启期间 `127.0.0.1:29610` 尚未监听。
