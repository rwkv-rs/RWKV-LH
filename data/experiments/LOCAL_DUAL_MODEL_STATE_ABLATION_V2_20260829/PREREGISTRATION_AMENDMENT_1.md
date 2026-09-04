# V2 预注册修订 1：新增五工具的数据源替换

登记时间：2026-08-29（Asia/Shanghai）

## 触发证据

第一次数据构建预检在写出数据目录前失败。固定的 `utf8-byte-5gram-cosine.v1`、`n=5`、
同 operation 阈值 `0.95` 检出 Round1 direct 补充行的同类模板重复；已观察最大值至少
`0.9893162393162392`。没有模型调用、训练、测试标签读取或数据产物写出。

不得为保留旧源放宽相似度阈值。原 V2 协议中 18 个本地 operation + final 的 coverage 来源、
所有 split、训练总量 2000、评价器和门槛均保持不变。

## 唯一修订

五个新增 operation 的来源由 Round1 direct 行替换为冻结的
`rwkv_lh_network_exact_tool_selector_v2_4/cases.jsonl` train/dev family：

- `web_search`
- `connector_lookup`
- `calculator`
- `date_diff`
- `current_time`

每个 source row 已有精确 stage objective、label、semantic family 和冻结 split。Executor target
只允许使用固定字符串/正则规则从 stage objective 抽取：查询/URL、结构化 connector 类型与
标识、完整算术表达式、两个 ISO 日期或 IANA timezone。抽取结果必须通过当前
`ActionDefinition`；模糊的 `package or repository` connector 变体排除，不能猜 operation。

- train：每类 58，共 290；与 coverage 的 1710 行合计 2000。
- dev：每类 20，共 100；与 coverage 的 380 行合计 480。
- test split 完全不纳入构建、训练或调参，仍留作后续冻结评价。
- 中英文只改变任务外层表达，不改变 path、identifier、query、expression、date 或 timezone。
- 相似度版本、阈值和比较字段不变；第二次预检仍必须零 violation。

本修订只修复数据源不满足原有门槛的根因，不改变门槛本身。
