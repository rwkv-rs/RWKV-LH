# Round118 v17 Basic30 人工因果分析

## 结论

Round118 完成了两个真实的结构修复，但没有恢复 Round46 的任务质量：

1. append-only `CausalEvent` 已成为唯一持久化事实源。官方 30 题的 751 个事件全部可以
   校验并重建投影；131/131 个已执行 Action 都是终态且具有完整 Result，Round117 的
   140/140 个 `running/result=null` 状态分裂已经消失。
2. 协议拒绝后，系统只把 RWKV 已选择 operation 的原始错误与精确 schema 返回给模型，
   不改参数、不换工具、不补值。B16/B17 从各 12 次 `max_start_byte` 重复拒绝降为各 1 次，
   并都完成了真实读取和写入。

任务质量只从 Round117 Strict `20/30` 小幅升至 `21/30`，低于 Round46 的 `24/30`；
FP 从 `8` 增至 `9`，Round46 TP 只保留 `17/24`。因此 v17 的内部事实结构和接口恢复成立，
但整个 agent 结构未过门，不能启动 confirmatory、collection 或 Full90。

本轮最重要的新证据是：接口阻塞移除后，B16/B17 的失败自然后移到真实语义阶段；B10 则
出现“模型错误策略 → 相同测试失败被系统当成不同失败 → prompt/rollover 放大 → RWKV 最终
说出正确修复方向却没有执行”的完整放大链。下一步应压缩和显式呈现客观因果状态，不应
恢复静态 Task DAG、同模型 reviewer 或隐藏验收 gate。

## 固定指标与整体比较

| 指标 | Round46 Full90 的 Basic30 | Round117 v15-B | Round118 v17 | 结论 |
| --- | ---: | ---: | ---: | --- |
| Strict / External | 24/30 | 20/30 | 21/30 | 较 Round117 +1，仍低于最佳 -3 |
| Agent completed | 25/30 | 28/30 | 30/30 | 已保证每题都有 Final，但非空不等于正确 |
| FP | 1 | 8 | 9 | 未达 `<=1`，且较 Round117 +1 |
| FN | 0 | 0 | 0 | 保持 |
| Round46 TP 保留 | 24/24 | 16/24 | 17/24 | 未达 `>=23/24` |
| 固定 40 项 byte-5gram similarity | 0.959895851803 | 0.827448750446 | 0.956612580586 | 非常接近但仍低于门槛；Strict/FP 同时失败 |
| 模型请求 | 474 | 220 | 186 | 仅作诊断 |
| prompt tokens | 919,718 | 939,702 | 818,711 | B10 一题占 335,914 |
| Action | 历史格式不可直接比 | 140 | 131 | Round118 全部可审计 |
| 协议拒绝 | 历史格式不可直接比 | 50 | 25 | 拒绝减半 |
| Final 非空 / raw 相等 | 历史仅 25 个 completed | 30/30 | 30/30 | 达标 |

Round118 相对 Round117 新增 PASS：B18、B26；丢失 PASS：B10，净增 1。B16/B17 虽然
从 blocked/未完成变成 completed，但业务产物错误，所以只是接口恢复，不是 Strict 提升。

### Round117 similarity 记录纠正

Round117 旧分析写的是 `0.902448750446`。本轮用冻结的
`utf8-byte-ngram-cosine.v1` 对同一 40 项重算，并首先精确复现 Round46 的
`0.959895851803`，得到 Round117 `0.827448750446`。差值正好是 `3/40`：Round117-B26
的 `A`/`A\n`、`B`/`B\n`、`C`/`C\n` 三个短文本在固定 byte-5gram 算法中相似度为 0，
不能按 1 计。Round118 的 `0.956612580586` 使用同一实现和 missing-zero 口径。该纠正
不改变 Round117/118 均未过门的结论，但以后必须以可复现脚本结果为准。

## 30 题逐题因果复核

| 题目 | 结果 | 第一条真实因果链 | 后续放大或质量判断 |
| --- | --- | --- | --- |
| B01 | PASS | 精确写 greeting → 读取同一文件 | 完整 write→observe→Final |
| B02 | PASS | list → 一次 `max_bytes` 拒绝 → 精确 schema 反馈 → read → 正确 write_json | 接口恢复有效；写后未再读取 |
| B03 | PASS | read_json → 保留无关字段并改值 → read_json | 完整 mutation→observe 链 |
| B04 | FAIL/FP | 读到正确 source，却显式写成 `archive/source.txt`，遗漏 `2026` | 后续 list/read 只验证了错误路径；RWKV 把错误主体绑定为自己的目标 |
| B05 | FAIL/FP | 选择 `replace_text(new="")` 而非 remove_line | 目标字符串消失但遗留空行；未观察最终字节 |
| B06 | PASS | 分别读取 A/B → 精确组合写入 | 多源 direct lane 成功；Final 声称读过 combined，但实际没有 |
| B07 | PASS | 读 production → 选择正确 endpoint | 分支正确；无写后观察 |
| B08 | PASS | 读 payload → 写正确 digest → `sha256sum` 核对源 | 业务正确；独立命令确认 digest |
| B09 | PASS | list/read CSV → 正确统计 JSON | 正确变换；无写后观察 |
| B10 | FAIL/FP | 读源码/测试 → 写朴素 replace → 测试失败 | 13 次近同失败被拆为 13 个 failure key；反复追加 `.strip('-')`，两次 rollover 后仍失败；Final 说出 regex 修复但未执行 |
| B11 | FAIL/FP | 读到首尾空格 → title case 后原样保留空格 | “trim”义务被忽略；无写后观察 |
| B12 | PASS | 读全部整数 → 正确 count/sum/min/max | 正确变换；无写后观察 |
| B13 | PASS | read_json → 正确修改 → read_json | 完整 mutation→observe 链 |
| B14 | FAIL/FP | 两个来源都读对，组合时在已有尾换行外又加空行 | 来源读取没问题，错误发生在字节拼接；无写后观察 |
| B15 | PASS | 读颜色 → 按首次出现去重 | 正确变换；无写后观察 |
| B16 | FAIL/FP | 一次 `max_start_byte` 拒绝后成功读取 | 只把 MODE 改为 prod，保留注释和空行；接口错误已消失，真实语义错误暴露 |
| B17 | FAIL/FP | 一次长 JSON 退化后成功读取并筛 active | count 正确但数组仍按输入顺序 `Zoe,Ada`，忽略 sorted |
| B18 | PASS | 读 price → 正确算 discount=12、total=68 | 相对 Round117 恢复；无写后观察，单次结果不足以证明稳定提升 |
| B19 | PASS | 读 payload → 写正确 SHA256 manifest | 正确；未用独立命令再算一次 |
| B20 | PASS | 读实现和测试 → 写 `value % 2 == 0` → unittest PASS | 强 coding 因果链 |
| B21 | PASS | 读 CSV → 正确聚合并写 JSON 文本 | 内容正确；无写后观察 |
| B22 | FAIL/FP | 读 JSON → Markdown 标题后多空行、文件尾再多空行 | 纯字节格式错误；无写后观察 |
| B23 | PASS | primary JSON 失败 Observation → 读 backup → 写正确 fallback | 负向观察正确驱动分支，证明失败事实可用 |
| B24 | FAIL/FP | 读完整日志 → 原样复制为 sorted.log | 去重和排序都未执行；无写后观察 |
| B25 | PASS | 读 base/override → 正确嵌套合并 | 多源结构化变换成功 |
| B26 | PASS | 写三个带换行文件 → list output → 逐个 read | 相对 Round117 恢复；完整集合与成员观察链 |
| B27 | PASS | 读配置 → replace all，Action 返回替换 3 次 | 产物正确；Final 的“无 v1”没有独立 read/grep |
| B28 | PASS | 读 key=value → 正确整数 JSON | 一次 schema 反馈后恢复；无写后观察 |
| B29 | PASS | 两次相同 list → read → 写副本/manifest | 结果正确；仍有轻微无进展重复但未放大 |
| B30 | PASS | 读实现/测试 → 写 split/join 实现 → unittest PASS | 强 coding 因果链 |

## 分环节归因

### 1. 模型边界：结构性恢复已成立

Round117 的拒绝分布为：`max_start_byte 24`、`read_file max_entries 10`、`max_bytes 6`、
非法/截断 JSON 5、缺参数 3、未注册 operation 1、`read_json max_entries 1`。

Round118 变为：`read_file max_entries 9`、`max_bytes 6`、非法/截断 JSON 6、
`max_start_byte 2`、`read_json max_entries 1`、缺参数 1。19 个能够识别已选 operation 的
拒绝都附带精确 schema（read_file 17、read_json 1、write_file 1）；6 个无法解析出一个
完整 JSON call 的拒绝没有猜 operation。Stage A canary 与官方运行的 7/7 外部结果一致，
所以 B16/B17 的接口恢复具有重复证据。

结论：精确 schema 反馈应保留。它只释放 RWKV 已作出的工具选择，没有替模型选择工具或
修改参数。它不是当前 9 个业务失败的共同首因。

### 2. RWKV 语义生成：9 个错误的第一来源

- 路径/主体错误：B04。
- 精确文本与格式变换错误：B05、B11、B14、B16、B22。
- 排序/集合业务变换错误：B17、B24。
- coding/recovery 策略错误：B10。

这些值都由 RWKV 明确输出，Harness 没有改写。B16/B17 尤其证明：正确源内容到达模型、
工具调用成功后，最终错误仍由模型生成。系统不能靠格式转换层把这些值变成标准答案。

### 3. Observation→下一决策：当前最值得修的放大层

多数正确题在 mutation 后也没有观察最终 artifact；9 个 FP 中，除 B04 验证了错误路径、
B10 收到失败测试外，其余均在错误写入后直接 Final。现有 instruction 已要求 observable
verification，但弱模型经常忽略。解决方式不能是 Controller 读取隐藏验收并否决 Final，
而应把客观状态显式、紧凑地投影给 RWKV：最新 artifact revision 是否在 mutation 后被
观察、最近 verifier 结果、相同 Observation 出现次数。

### 4. Recovery/rollover：B10 的联合放大链

B10 的首个错误是 RWKV 选择了只能压缩一次连续空格的 `.replace('--','-')`。架构随后
放大错误：

1. 同一个测试断言反复失败，但 failure key 同时绑定 workspace digest；每次无效改代码都会
   改 workspace digest，因此 13 个 key 的计数全部是 1。
2. rollover 机械保留最后 12 个 Action，恰好保留一串近同的 write→FAIL，未折叠成
   “相同测试结果重复 N 次”的客观事实。
3. B10 单题使用 38 requests、33 Actions、335,914 prompt tokens，占全轮 prompt 的 41%。
4. 最终 RWKV 已在 Final 中提出正确 regex 方向，却没有再执行；Controller 按原则原样返回，
   外部验收正确判 FAIL。

所以 B10 不是单纯“模型差”，而是模型先错、失败身份和 replay 设计再放大。必须把
**执行重试身份**与**Observation 等价身份**拆开：前者继续包含 workspace/revision 以保证
副作用安全；后者只对精确 ActionResult 建 digest 并累计 repeat count。repeat count 只作为
事实显示给 RWKV，不能由 Controller 据此生成修复或答案。

### 5. 持久化与 Final：边界行为正确

- 751 个 causal events 的 sequence/parent/digest/payload schema 全部通过 reload。
- 131/131 Action 均为 succeeded/failed 终态且 result 非空。
- Final 30/30 非空，30/30 与 RWKV raw text 字节相等。
- 9 个错误 Final 没有被 Controller 修正或隐藏；这符合“不作弊”，也使 FP 真实可见。

## 下一轮建议：v18 Causal Observation Projection

只做一个新的单变量结构实验，不加角色、不加语义 gate：

1. 保留 v17 的 direct per-operation interface、唯一 CausalEvent authority、raw Final、uv
   Python、sandbox 与精确 schema feedback。
2. 把当前 failure key 拆成：
   - `execution_identity`：operation、完整 arguments、workspace/artifact revision，用于重放安全；
   - `observation_fingerprint`：精确 Result 的 outcome/exit/error/output digest，用于客观重复计数。
3. 每次请求从事件链确定性生成一个 model-visible state capsule，而不是继续堆完整 replay：
   immutable request、最新 workspace manifest、每个 subject 的最新 Observation、最新 mutation
   revision 是否有后续 observation、相同 observation repeat count、最后一次协议拒绝。
4. rollover 对相同 observation fingerprint 折叠计数，保留首次和最新的原始 Result 引用，
   不再机械保留 12 个近同 Action。
5. Controller 仍允许 RWKV 选择任意注册工具或 Final；不得根据 repeat count、未观察 revision
   或隐藏验收自动选择工具、生成参数、改写产物、否决或改写 Final。

首个 canary 应是 B10，并加入 B20/B30 防 coding 回归；随后用 B04/B05/B11/B14/B16/B17/
B22/B24 检查“显式 observation 状态”是否让模型自行复核。通过后再跑固定 Basic30。若仍未
达到 Round46，应再单独预注册 model-owned local focus 实验；不能恢复静态 Task DAG 或
Goal reviewer，因为 Round116 已证明它们会重新引入双进度系统。

## 运行与审计完整性

- 预登记：`data/experiments/Round118_V17_CAUSAL_EVENT_AUTHORITY_AND_SCHEMA_FEEDBACK_PROTOCOL.md`
- 官方输出：本目录 `REPORT.md`、`results.json`、30 个 case audit/model trace。
- 离线回归：`99 passed`；统一 control：`61 passed`；E2E catalog：`90/90`；compileall 与
  `git diff --check` 通过。
- source manifest：47/47 hash 匹配，mismatch 0；官方运行中途未修改源码、测试、数据或口径。
- 模型：`rwkv7-g1i-13.3b-20260805-ctx16384`；temperature 0.05、top-p 1、top-k 0；
  `max-transitions=200`、concurrency 1、WSL UbuntuRecovered、uv 0.12.5。
- 曾误把 runner 的 `core30` 理解为 B01–B30，错误运行已终止并保存在
  `Round118_v17_INVALID_wrong_core30_aborted_20260815`，明确不计入任何官方指标。
- Stage A 未过门，因此没有运行 confirmatory、collection 或 Full90。
