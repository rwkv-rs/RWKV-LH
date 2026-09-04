# Round117 v15-B Basic30 人工因果分析

## 结论

Round117 的单 RWKV direct-action spine 是一次明显的整体质量恢复，但不是可接受的最终
结构：Strict/External 从 Round116 的 `8/30` 恢复到 `20/30`，FP 从 `20` 降至 `8`，
FN 保持 `0`，固定 40 项 missing-zero artifact similarity 从 `0.455076063142` 恢复到
`0.902448750446`。它证明删除在线 Task DAG、`lh_task_call` 通用操作外壳和重复 reviewer
是正确方向。

它仍没有达到预注册门槛，也没有恢复 Round46：Round46 Basic30 为 Strict `24/30`、
FP `1`、FN `0`、similarity `0.959895851803`。Round117 只保住 Round46 的 `16/24`
个真阳性。因此不运行 confirmatory、collection 或 full E2E-90。

更重要的是，人工审计发现一个覆盖全部 30 题的持久化一致性缺陷：140 个实际执行过的
Action 在最终 `RunState.actions` 中全部仍为 `running` 且 `result=null`。正确 ActionResult
只存在于 `model_events`/Observation。现有统一 `CausalEnvelope` 因而只是第二份旁路记录，
还不是唯一权威事实源。Round117 应以“方向有效、实现未通过”处理。

## 固定指标与整体对比

| 指标 | Round46 Basic30 | Round116 v15-A | Round117 v15-B | 判断 |
| --- | ---: | ---: | ---: | --- |
| Strict | 24/30 | 8/30 | 20/30 | 较 v15-A +12，仍低于最佳 -4 |
| External | 24/30 | 8/30 | 20/30 | 同上 |
| Agent completed | 25/30 | 28/30 | 28/30 | 非空结束不能代表任务正确 |
| FP | 1 | 20 | 8 | 大幅下降，仍未达到 `<=1` |
| FN | 0 | 0 | 0 | 保持 |
| Round46 TP 保留 | 24/24 | 6/24 | 16/24 | 未达到 `>=23/24` |
| missing-zero similarity / 40 | 0.959895851803 | 0.455076063142 | 0.902448750446 | 未过门 |
| 模型请求 | 474 | 408 | 220 | direct spine 更紧凑 |
| 总 prompt tokens | 919,718 | 1,224,367 | 939,702 | 请求减少，但 prompt replay 仍重 |
| Action | — | — | 140 | 其中 140/140 持久状态错误 |
| 协议拒绝 | — | — | 50 | 24 次集中在 B16/B17 |
| Final 非空/raw 相等 | — | — | 30/30 | 达标 |

Round117 相对 Round116 新增 17 个 PASS、丢失 5 个 PASS，净增 12；相对 Round46
丢失 B05/B11/B14/B16/B17/B18/B24/B26，新增 B23/B27/B29/B30。

## 逐题人工复核

| 题目 | 结果 | 第一处偏离或正确因果链 | 后续放大/结论 |
| --- | --- | --- | --- |
| B01 | PASS | RWKV 直接写入精确文本，再读取核验 | 理想的 write→observe→Final 链 |
| B02 | PASS | list→read input→写出正确 report.json | v15-A 的 Task/Action 脱节消失；两次 `max_bytes` 拒绝后自行纠正 |
| B03 | PASS | read_json→正确改写→读取核验 | v15-A 的同义 Task 扩展消失 |
| B04 | FAIL/FP | 读取 source 后显式写到 `archive/source.txt`，遗漏要求的 `archive/2026/` 层级 | Harness 忠实执行错误路径；两次 read 参数拒绝可能增加漂移，但不是错误路径的生成者 |
| B05 | FAIL/FP | RWKV 选择 `replace_text(new="")` 而非已注册的 `remove_line` | 目标行文本消失但留下空行，字节级验收失败；Controller 未改写输出 |
| B06 | PASS | 依次读取 part_a、part_b，再一次写出正确 combined | 证明同一 direct lane 能完成多源协调，修复 v15-A 的“一 Task 一 Action”截断 |
| B07 | PASS | 读取 mode 后写出正确 endpoint | 三次格式拒绝后恢复，producer 因果关系正确 |
| B08 | PASS/风险 | 第二个 Action 已生成正确 manifest | 随后又做 16 次交替读取并重复写 manifest；结果正确但缺少客观 unchanged-observation 提示 |
| B09 | PASS | 读取 CSV 后写出正确 JSON | 一次 `max_entries` 拒绝后恢复 |
| B10 | PASS | 读取源码和测试、修改代码、运行 unittest 通过 | 直接证明当前结构可完成小型 coding task |
| B11 | FAIL/FP | 读取带空格名称后写成保留首尾空格的 title case | 纯 RWKV 变换错误；写后未观察，Final 直接宣称完成 |
| B12 | PASS | 读取数字、计算统计并写出精确产物 | 一次截断的非 JSON 输出后恢复 |
| B13 | PASS | 读取配置、正确更新并读取核验 | v15-A 的恢复阻塞消失 |
| B14 | FAIL/FP | 两个来源均已读取，但拼接时保留来源尾换行又额外插入 `\n--\n` | 分隔符两侧多空行；跨文件读取成功，错误发生在 RWKV 字节组合阶段 |
| B15 | PASS | 读取颜色并按首次出现顺序去重 | 一次正确写入，无旧 evidence subject 冲突 |
| B16 | FAIL/未完成 | list 成功后 12 次输出 `read_file(max_start_byte=...)` | 参数拒绝只返回错误，没有把已选 read_file 的最小精确 schema 放到最近上下文；预算终止 |
| B17 | FAIL/未完成 | 与 B16 相同，12 次重复 `max_start_byte` | 同一接口恢复缺陷，不是独立业务错误 |
| B18 | FAIL/FP | 正确读到 subtotal=80、discount_rate=0.15，却写出 total=92 | RWKV 把折扣加到 subtotal；schema/字段正确，属显式算术语义错误 |
| B19 | PASS | 读取源字节并写出正确 SHA256 manifest | 一次 read 参数拒绝后恢复 |
| B20 | PASS | 读取实现和测试、写代码、运行测试通过 | uv/Python coding 链有效 |
| B21 | PASS | 读取 CSV、聚合分类数量、写出正确 JSON | 一次长输出截断后恢复 |
| B22 | FAIL/FP | 内容项目正确，但写成标题后有空行且文件尾多一个空行 | 纯字节格式错误；写后未读取核验 |
| B23 | PASS | primary JSON 解析失败的负向 Observation 被保留，随后读取 backup 并正确写入 | 证明 exact ActionResult 可支撑 fallback，优于 Round46 |
| B24 | FAIL/FP | RWKV 原样写出含重复且未排序的日志 | 已读到完整源，错误发生在去重/排序变换；写后未核验 |
| B25 | PASS | 读取 base/override 后正确合并嵌套字段 | direct lane 的多源结构化合并有效 |
| B26 | FAIL/FP | 正确创建 A/B/C 三个文件，但内容均缺少尾换行 | 文件集合正确，统一的字节格式错误；一次 missing content 拒绝后恢复 |
| B27 | PASS | read→replace all→read，产物精确 | 修复旧 selector/直接工具冲突，优于 Round46 |
| B28 | PASS | key=value 转整数 JSON 正确 | 一次 read 参数拒绝后恢复 |
| B29 | PASS/风险 | 前 33 个 Action 全是相同 list_directory，随后才 read→write→write | 最终正确且优于 Round46，但无进展循环仍会放大长任务漂移风险 |
| B30 | PASS | 读取源码和测试、实现函数、运行测试通过 | coding 链有效，优于 Round46 |

## 失败聚类与共同原因

10 个 External FAIL 可分为四类，而不是 10 个独立补丁：

1. **接口恢复阻塞 2 题**：B16/B17。两题共享完全相同的 `max_start_byte` 重复链，24 次
   协议拒绝。它们是架构可以消除的失败。
2. **字节/格式生成错误 5 题**：B05/B11/B14/B22/B26。Harness 执行了 RWKV 明确给出的
   值，没有替模型决定。这些不能靠 hidden verifier、答案改写或字段丢弃修复。
3. **业务变换错误 2 题**：B18/B24。源事实正确到达模型，错误由 RWKV 在算术、去重和排序
   阶段产生。
4. **路径层级错误 1 题**：B04。模型显式选择错误目标路径。

Round46 的八个被丢失 TP 有共同的历史差异：B11/B14/B18/B24 在局部 Task 中直接生成
正确产物，并有后续读取；B16 有 read→write→read；B17 有 read_json 后的结构化写入；
B26 把目录和每个文件拆成局部 Action；B05 的第二次 RWKV 工具选择选中了 `remove_line`。
这说明 Round46 的收益来自**局部聚焦和真实 Observation 后继续行动的机会**，不是 reviewer
正确性本身。不能因此恢复静态 Task DAG、criterion/evidence 预猜或同模型 completion judge；
应在单 lane 中保留模型自己的局部意图和客观 revision-observation 状态。

## 统一字段的审计结论

Round117 已引入共同字段：

```text
id / parent_id / kind / name / status / payload / refs / digest
```

方向正确，但当前实现仍有三个结构问题：

1. `CausalEnvelope` 与 `RunState.actions`、`model_events`、artifact revision 同时保存事实，
   不是唯一权威源；本轮 140/140 Action 状态分裂就是直接证据。
2. `kind` 由 event name 的字符串前缀推断，新增事件名可能被静默归到错误 kind。
3. Action 开始后 `_persist` 用深拷贝替换 `state.__dict__`，Controller 继续修改旧的局部
   `ActionRecord` 引用；Observation 正确、Action ledger 错误。测试没有断言最终持久化的
   status/result，因此未发现。

下一版的通用字段不能只是“再写一份日志”，而必须成为单一 append-only 事实链。建议的
最小 v2 形状是：

```text
schema_version / event_id / run_id / sequence / parent_id / cause_id /
subject_id / event_type / payload_schema / payload / digest / created_at
```

- `event_type` 显式枚举，不从名字猜 kind；`payload_schema` 版本化每种 payload。
- Action 使用 `action_started` 和 `action_finished` 两个不可变事件，不回头修改旧对象。
- model call、protocol result、Action、Observation、artifact revision、Final 都只追加事件。
- Action ledger、UI 步骤、恢复快照是对事件链的确定性 fold/cache；加载时校验投影 digest，
  不能成为第二事实源。
- `cause_id` 表示直接因果，`subject_id` 聚合同一个 request/action/artifact；`parent_id` 只
  表示全局追加顺序，避免把三种关系混在 `refs` 中。
- 模型边界仍使用每个 Harness operation 的精确 schema；不得重新引入
  `operation + operation_args`。通用字段是内部运输协议，不是通用工具参数。

## 下一步边界

P0 先修事实权威，不做在线调参：

1. 将 Action 生命周期改成 append-only start/finish 事件，并删除独立可变 Action 真相。
2. 补持久化、重启、side-effect crash、artifact revision、UI projection 回归；必须断言
   已执行 Action 在 reload 后具有准确 status/result。
3. 对全部预运行 source-tree manifest 做只读 hash 检查。

随后才可预注册一个模型可见变量：协议拒绝后，把 **RWKV 已经选择的那个 operation** 的
精确 schema 和原始拒绝原因放到最近上下文。Controller 不选择 operation、不补/删参数、
不把 `max_start_byte` 猜成其他字段。B16/B17 是主 canary，B02/B06/B07/B19/B28 是不得
退化的格式恢复控制组。

暂不加入 reviewer、隐藏验收 gate、Task DAG、答案筛选或大量格式别名。B08/B29 的相同
Observation 重复可在后续以客观 repeat count 暴露给 RWKV，但不能由 Controller据此判断
任务完成。格式/业务错误是否需要 model-owned scratchpad 或 revision-observation 提示，
应在 P0 后另行单变量预注册，不能和状态修复混在一次实验中。

## 证据与实验完整性

- 官方结果：`REPORT.md`、`results.json` 和各题 `audit.json/model_trace.json`。
- 模型请求 `220`、Action `140`、拒绝 `50`；拒绝分布为：
  `max_start_byte 24`、`max_entries(read_file) 10`、`max_bytes 6`、截断 JSON `5`、
  write_file missing content `3`、未注册 verify_sha256 `1`、read_json max_entries `1`。
- 预运行 `source_tree_manifest.json` 含 53 个文件；审计后逐文件复核为 `53/53` 匹配、
  mismatch `0`，所以运行时代码未在官方运行中途改变。
- `Round117_v15b_source_manifest.json` 最初文件 birth time 为 18:03:16，官方运行于
  18:03:30 开始；审计时曾误把生成脚本当检查器运行，于 18:16:03 重写了该辅助 manifest
  的时间/status 元数据。没有改 runtime 或官方结果，且独立的预运行
  `source_tree_manifest.json` 仍完整；但这个辅助 manifest 不再单独作为“未重写”证据。
  生成脚本现已增加只读 `--check` 和拒绝默认覆盖保护。
