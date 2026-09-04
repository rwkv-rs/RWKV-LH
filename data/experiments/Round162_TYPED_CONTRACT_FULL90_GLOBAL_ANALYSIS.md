# Round162 Typed Contract Full90 全局分析

日期：2026-08-23

## 结论

本轮按用户要求完整运行固定 RWKV-E2E-90，90/90 均进入终态，最终分类为
`TP=14 / FP=3 / FN=21 / OTHER=52`。当前架构不能替换 R126，也不能标记为 Full90-ready。

最重要的结论不是“出现了很多不同的小 bug”，而是 76 个非 strict 结果主要由三个共享根因
产生：

1. 37 例没有获得有效 contract plan，全部 0 RWKV action；其中 35 例是 terra 与 sol 的传输
   路由最终均失败，2 例是 Planner 输出在 semantic repair 后仍不满足本地约束。
2. Planner 输出的 typed IR 只在 JSON 形状上“有类型”，没有通过算子语义和数据类型编译。
   在拿到计划的 53 例中，机械检出 42 个不可按当前 evaluator 语义执行的 assertion，覆盖
   20 例，并同时造成 FN、FP 和额外 Reviewer 调用。
3. latest-state capsule 把同一路径的 content、digest、mutation receipt 和 command output 压成
   一个视图；无 artifact 的事务内 action 还会继承同 atom 的 artifact。正确文件内容因此会被
   `file_digest`、`check_command` 或 `write_json` 的输出覆盖，本地 checker 随后稳定地误判。

因此，中转站不稳定是重要根因，但不是唯一根因。排除 37 个零 action case 后，53 个有计划
case 的 external pass 为 `35/53=66.0%`，strict TP 却只有 `14/53=26.4%`。RWKV 实际成品能力
没有像 strict 分数那样崩塌；主要损失发生在 Planner→Contract→Evidence→Acceptance 控制链。

## 实验完整性

- 协议：`Round162_USER_REQUESTED_TYPED_CONTRACT_FULL90_PROTOCOL.md`。
- 原始目录：`Round162_typed_contract_full90_20260823/`，约 198 MiB。
- 固定数据：RWKV-E2E-90 v1，B30/M30/H18/LH12，case concurrency=4。
- 运行时间：约 15,063 秒，即 4 小时 11 分；运行中没有修改代码、模型、阈值或评价口径。
- 运行前最终单测：168 passed；正式 runner 因 strict 未全通过按设计返回 code 2。
- 状态：completed=17、interrupted=73、running=0；runner 和 4 个 worker 已正常退出，无残留进程。
- 90 个结果和逐例 audit 均已持久化；Supervisor 工具执行为 0，17 个 completed Final 均与
  raw RWKV Final 一致。
- 统一异常终态有效：B11 的 graph runtime `ValueError` 被记录为
  `contract_graph_runtime_failure`，没有再留下 running。
- H03、H17 的 benchmark resume 在同一 run_id 下各追加了第二个 terminal event。因此 90 例
  都有最终终态，但只有 88/90 满足“恰好一个 terminal event”；resume 生命周期仍需整改。

## 固定指标

| 层级 | TP | FP | FN | OTHER | external passed |
|---|---:|---:|---:|---:|---:|
| B | 7 | 1 | 15 | 7 | 22 |
| M | 6 | 1 | 5 | 18 | 11 |
| H | 1 | 0 | 1 | 16 | 2 |
| LH | 0 | 1 | 0 | 11 | 0 |
| 总计 | 14 | 3 | 21 | 52 | 35 |

验收 precision 为 `14/17=82.4%`，但对真实 external success 的 recall 只有
`14/35=40.0%`。Round158 对应 precision 为 `34/43=79.1%`、recall 为
`34/38=89.5%`。这版只小幅提高验收 precision，却把正确产物的收口率降低了约 49.5 个百分点。

参考门结果：

| 指标 | 参考门 | Round162 | 结果 |
|---|---:|---:|:---:|
| 90 例持久化 | 90 | 90 | PASS |
| running | 0 | 0 | PASS |
| 每例唯一 terminal | 90 | 88 | FAIL |
| strict TP | >41 | 14 | FAIL |
| FP | <=9 | 3 | PASS |
| FN | <=1 | 21 | FAIL |
| logical GPT | <344 | 373 | FAIL |
| GPT total tokens | <4,506,270 | 1,727,942 | PASS |
| B/M/H/LH TP | >=24/11/3/1 | 7/6/1/0 | FAIL |

## 与历史基线的整体比较

| 轮次 | TP | FP | FN | OTHER | logical | physical | returned | GPT tokens | RWKV actions |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| R126 canonical | 36 | 30 | 0 | 24 | - | - | - | - | - |
| Round148 atom graph v4 | 41 | 16 | 2 | 31 | 521 | - | - | 3,309,497 | 624 |
| Round158 contract graph | 34 | 9 | 4 | 43 | 344 | 451 | 319 | 4,506,270 | 560 |
| Round162 typed transaction | 14 | 3 | 21 | 52 | 373 | 629 | 278 | 1,727,942 | 520 |

相对 Round158：

- TP 减少 20（-58.8%），FN 增加 17；external passed 只从 38 降到 35，说明大部分 strict
  损失来自控制器，而不是 RWKV 产物。
- logical 增加 29（+8.4%），physical 增加 178（+39.5%），returned 减少 41（-12.9%）。
- total tokens 减少 2,778,328（-61.7%），latest capsules 和 local review 的压缩方向有效；
  但每个 strict TP 仍需 26.64 logical calls，Round158 只有 10.12。
- actions 减少 40（-7.1%），protocol rejects 为 181，几乎等于 Round158 的 182。
- 旧 34 个 TP 中仅 10 个保持 TP，20 个变成 FN，4 个变成 OTHER；本轮新增 4 个 TP，净损失 20。
- Round158 的 9 个 FP 中，3 个仍是 FP，只有 M19 真正变成 TP；4 个只是因 plan unavailable
  变成 OTHER，M26 因中断变成 OTHER。因此 FP 从 9 降到 3 主要是 fail-closed，不是完整修复。

Round161 15-case canary 与本轮同 15 例有 5/15 分类变化：B13、B21、LH06、M05、M08。
M05 从 TP 变 OTHER，LH06 从 OTHER 变 FP。这说明真实路由和在线 Planner 仍存在显著运行间波动。

## 全局根因一：Planner 路由在真实 contract workload 下不稳定

37 例最终 `contract_plan_unavailable`，层级分布为 B2/M12/H12/LH11，全部 0 RWKV action：

- 35 例为传输最终失败；2 例为 plan semantic validation 最终失败（B24、LH09）。
- GPT logical/physical/returned=`373/629/278`。
- contract plan logical=267，exception review logical=106。
- terra plan started/returned=`208/149`，逻辑返回率 71.6%；sol fallback started/returned=
  `59/23`，逻辑返回率 39.0%。
- terra Reviewer started/returned=`106/106`。同一模型在较短 review phase 为 100% 返回，
  但在较长 strict Planner phase 明显不稳定，故障是 phase/request-shape sensitive，不是简单的
  “terra 整体不可用”。
- reasoning fallback=143、model fallback=59、request failed=95、semantic rejected=15。
- 冷 cache 下 stored=157、hit=0；cache 对首次任务和首次 correction 无法降低本轮调用。
- 成功返回延迟中位数 82.5 秒，P95 105.6 秒。GPT 全局串行使一个长尾请求阻塞其他廉价
  RWKV worker，Full90 用时从 Round158 约 2h36m 增至约 4h11m。

这 37 例解释 37 个 OTHER，但不解释 21 FN、3 FP 和另外 15 个 OTHER。

## 全局根因二：Typed IR 不是可执行的强类型 IR

53 个成功提交初始计划的 case 共生成 115 个 obligations、342 个 assertions、15 种 kind。
本地 schema 能检查字段存在，却没有检查“该 kind 的 evaluator 实际能否表达 Planner 写入的
关系”。机械扫描发现 42 个唯一 assertion 存在明确语义类型错误，覆盖 20 例：

- 18 个 `json_value_from_source` 提供 2--4 个 source，但 evaluator 只比较第一个 source。
- 16 个 source 对 `.txt`、`.log` 或 `.md` 使用 JSON pointer，本地 parser 必然无法解析。
- 8 个 `json_value_from_source.expected` 写入 filter/dedup/round/merge 等自然语言变换，
  evaluator 完全忽略这段变换并做直接相等比较。
- 4 个 `numeric_aggregate.algorithm` 使用空值或 `lines`，不在 count/sum/minimum/maximum 中。
- 上述错误有重叠，因此是 46 个错误标记、42 个唯一 assertions；其 20 例结果为
  TP3/FP2/FN9/OTHER6。

另外，当前 schema 仍允许无法机械解释的语义写入“可执行”字段：

- B02 把 key-value 文本整体当成 `/project` JSON source，并把“count 乘二”编码成 `count`。
- B05 用 mutation 后的同一路径表示“保留 mutation 前内容”，latest-only 状态无法表达 pre-state。
- B07 的 `text_exact` 丢失末尾 newline，正确文件被判错。
- B17 把 filter 结果编码成“输出数组等于完整 users.json”。
- B27 同时要求同一 latest 文件包含旧 `protocol=v1` 和新 `protocol=v2`，把 pre/post 条件合并。
- B30、M20 把自然语言函数行为描述放进 `text_template`，checker 按源码字面子串查找。

这些不是 RWKV 执行错误，而是 contract compiler 错误。由于 obligation 在 revision 0 后冻结，
后续 correction 无权修复错误契约，只能反复要求 RWKV 修改已经正确的成品。

三个 FP 也都来自同一根因：

- B25 的 Planner contract 把 `enabled` 放进 `nested`，Reviewer 按错误 contract 接受。
- M29 的 contract 没有可靠表达 `translations` 容器和 missing-key 差集，Reviewer 接受错误结构。
- LH06 用多 source 关系表达 authority resolution，local checker 无法执行，exception Reviewer
  又接受了错误 key 名、错误外层结构和不完整 evidence。

三例都是 Round158 已存在的 FP；新 typed IR 没有真正修复它们。

## 全局根因三：latest-state 把不同证据视图错误折叠

当前 capsule 先把 action 关联到 artifact，再按 path 只保留“最后一个 capsule”。但一个 path
至少有四种不同事实：content、parsed JSON、digest/identity、mutation receipt。它们不能互相覆盖。

机械复核得到：

- 9 例中，typed content assertion 的最后 path view 被非 content operation 覆盖：
  `file_digest` 6 例、`check_command` 2 例、`write_json` 1 例；结果为 FN5/OTHER4。
- 7 例存在“action 自己没有 artifact，却继承同 atom 的全部 artifact”，共 18 个 action；
  结果为 TP1/FN4/OTHER2。

B20 是完整可复核入口：RWKV 写入正确 `parity.py`，随后 read 得到正确源码，测试也 exit 0；
但 transaction 的 `check_command` 没有 artifact，构造 capsule 时继承了 `parity.py`。按 path
取 latest 后，checker 实际拿测试日志去检查源码是否包含 `def is_even`，于是稳定地产生 FN，
并重复 read/rewrite/retest 正确文件。

这说明“只给强模型结果、不给过程”的方向正确，但压缩键错误。应该压缩为每个 path 的最新
typed view，而不是每个 path 只留一个任意 operation output。

## 全局根因四：Correction signature 没有压缩语义重复

34 个 evidence-stagnant case 包含 FN19/OTHER15；另有 M09 因 patch budget exhausted 成为 FN。
stagnant 簇消耗：

- 366 RWKV actions，占全部 520 的 70.4%。
- 210 logical GPT，占全部 373 的 56.3%。
- 280 physical GPT。
- 1,207,028 tokens，占全部 1,727,942 的 69.9%。

本轮提交 93 个 correction signatures，93 个全部唯一，duplicate block=0；与此同时仍有 34 例
因 evidence stagnant 停止。签名把新 correction node/operation result 造成的表面变化视为新状态，
没有识别“同一错误 contract、同一 artifact hash、同一缺失 evidence view”的语义重复。

当前纠错还没有区分三种完全不同的情况：

1. artifact 错误：需要 RWKV mutation transaction。
2. artifact 正确但 evidence view 缺失：只需要 RWKV read/check transaction。
3. contract 本身不可执行或与原请求不一致：不得再次修改 artifact，应回到 contract compiler
   或 exception Reviewer。

把三者都交给 Planner 追加 correction nodes，必然产生当前的成本和 FN。

## 全局根因五：窄事务和并行只部分落地

- 459 个 planned nodes 中 375 个（81.7%）仍只允许一种 operation，只有 84 个是多 operation。
- 410 个实际 atom outcomes 中，308 个只有 1 action，99 个有 2--4 actions，3 个为 0 action；
  实际多 action transaction 占 24.1%。
- 只有 10 个 case 存在真实 atom 时间重叠，Round158 为 35 个。
- RWKV model requests=1,111、actions=520、protocol rejects=181。

因此目标中的“GPT 拆成窄事务，多个 RWKV 并行完成”只在少数计划里出现。大量节点仍是单步
read、单步 write、单步 verify；37 个零计划 case 和强模型全局串行又进一步压低并行利用率。

## 五项改造的最终判定

| 改造 | 已成立部分 | 全量暴露的缺陷 | 判定 |
|---|---|---|:---:|
| Typed Contract IR | 342 assertions 可审计、revision 0 后冻结 | 无 kind-specific 类型编译，允许 prose/非法 source/operator | FAIL |
| Local checker + exception Reviewer | 49 次 local-only，106 次 mixed；GPT 不执行工具 | 错 IR 被确定性误判，错 contract 又被 Reviewer 接受 | FAIL |
| RWKV narrow transaction | 支持 2--4 actions，同 state 可 read→mutate→verify | 81.7% planned nodes 仍单 operation，实际 multi-action 仅 24.1% | FAIL |
| latest capsule + signature | tokens 降 61.7%，Reviewer 只见 result | path view 混淆；93 个签名无一 block，34 例仍 stagnant | FAIL |
| routing + terminal/scope | fallback/circuit/cache 有审计；running=0；runtime 统一终态 | 37 plan unavailable；H03/H17 双 terminal；B11 graph recovery 校验异常 | PARTIAL |

## 更适合当前目标的整体架构

目标仍应保持：强模型只负责 Planner/Reviewer，RWKV 是唯一工具操作者，强模型只接收执行结果，
不接收 RWKV 过程。需要改变的是中间的 contract compiler 和 evidence kernel。

### 1. Strong Planner 一次生成“可编译 DSL”，不是 prose assertion

Planner 输出的 executable fields 必须使用封闭 operator AST：

- scalar：constant equality、source equality、digest equality。
- collection：map/filter/dedup/sort/count/sum/difference。
- structure：exact keys、preserve、merge precedence、JSON pointer mapping。
- text：literal contains/excludes、format(template, sources)、line transform、newline policy。
- state selector：`initial`、`latest`、指定 revision，显式区分 mutation 前后状态。

每个 kind 使用条件 JSON Schema，禁止无关字段；本地 compiler 必须做 source media type、pointer、
operator arity、result type 和 evaluator capability 检查。不能编译的要求应显式标记为
`semantic_exception`，交给 Reviewer，而不是伪装成可机械执行的 assertion。

contract 只有在本地 type-check 和 request-clause coverage 都通过后才能冻结。失败最多进行一次
Planner repair；不得先冻结错 contract，再让 RWKV 无限修 artifact。

### 2. Evidence store 按 typed view 压缩

每个 path 至少分别保留：

- latest complete content/read view；
- latest parsed JSON view；
- latest identity/digest view；
- latest mutation receipt；
- command/check result 按 command identity 独立保存。

action 与 artifact 必须按 action_id 精确关联；artifact-less action 的 artifact 集必须为空，禁止
fallback 继承整个 atom。`write_file` 的 `file written`、`file_digest` 的 metadata、测试日志都不能
作为文件 content。latest key 应为 `(path, view_kind)`；无 artifact fact 应按稳定 operation/command
identity 压缩，不得把 correction node_id 纳入语义状态。

### 3. Acceptance 只对“可比较值”给 true/false

- source 或 target 未解析、operator 不支持、类型不匹配时必须返回 unresolved，绝不能返回 false。
- local checker 处理全部已编译 assertion；只有 explicit semantic_exception/unresolved 才调用强
  Reviewer。
- Reviewer 同时看到原始 request clause、编译后的 assertion 和最新 typed evidence；原始请求
  始终高于 Planner predicate，Reviewer 不得仅证明“错 contract 自洽”。
- deterministic contradiction 不应再触发 GPT 重读相同 evidence；先判断是 artifact mismatch 还是
  contract compiler defect。

### 4. Correction 改为本地分类路由，强模型不参与常规循环

- artifact mismatch：派发一个 RWKV recovery transaction。
- evidence missing：派发一个只读 RWKV verification transaction。
- contract invalid/unresolved：一次 exception Reviewer 或 contract repair，不修改 artifact。
- transport failure：durable queue/cached plan resume，不把 case 立即终止为 0-action。

签名固定为 `(unsatisfied assertion ids, typed initial/latest values, artifact hashes, normalized errors,
recovery class)`；忽略 node_id、普通命令输出和新 patch id。同签名第二次出现必须切换 recovery class
或安全停止，不能再调用 GPT/RWKV 做同构操作。

### 5. Planner/Reviewer 路由按 phase 解耦

本轮 terra Reviewer 106/106 返回，而 terra Planner 只有 149/208 返回。下一轮应保留 phase-specific
路由：短 result-only Reviewer 可继续使用 terra；Planner 改用更紧凑 DSL、较小输出和独立健康门，
并重新对候选模型做真实 contract workload canary，不能用 `/models` 或简单 JSON probe 代替。

circuit state 应在 4 个 worker 之间共享，避免每个进程重复打满失败 primary；强模型队列允许少量
并发而不是全局单锁。API 目标应是正常 case 1 次 Planner、机械任务 0 次 Reviewer、语义任务最多
1 次 Reviewer；常规 correction 不再调用强 Planner。

### 6. RWKV transaction 成为调度基本单位

Planner 直接输出同 scope transaction，而不是 read/write/verify 三个单步节点。mutation transaction
必须有 2--4 action budget，并在同一 RWKV state 中完成 inspect→mutate→verify；多个无写冲突
transaction 由本地 scheduler 并行。finalizer 只消费 typed evidence，不再制造新的业务修改。

### 7. Resume 使用 attempt epoch

`run_id` 下新增 attempt epoch；旧 terminal 被 resume 时记录 `run_resumed`，每个 attempt 恰好一个
terminal，整个 run 只保留一个最终 terminal projection。B11 的 recovery 关系也应由“成功 correction
覆盖失败 work”显式表示，finalizer 不应因已恢复的旧失败节点抛出全局 ValueError。

## 下一轮验证顺序

不应立刻再花一次 Full90 API：

1. 先对本轮 53 个已提交 plan 的 audit 做离线全量 replay，要求 342 个 assertions 全部通过新
   compiler 类型检查，0 个 content view 被 digest/command/mutation receipt 覆盖。
2. 用固定系统性集合验证所有 21 FN、3 FP、B11 runtime、H03/H17 resume；集合用于覆盖根因，
   不为 task_id 添加特判。评价仍使用原 external verifier。
3. 路由单独用真实 compact Planner schema 做 phase canary，预注册 logical/physical/latency 门。
4. 只有上述门通过才再跑 Full90；目标至少先恢复 Round158 的 TP34，同时保持 FP<=9、FN<=1，
   再挑战 R126/Round148。

## 作为 state-tuning 数据的使用方式

- 14 TP：可作为 clean positive transaction seed，但仍需保留 contract、action/result refs 和
  external checks。
- 21 FN：external artifact 是正目标，RWKV 成功 action 可以成为 worker 正种子；错误 typed
  assertion、重复 correction 和 interrupt decision 是负种子。不得把整条轨迹统一标正。
- 3 FP：只作为 contract/Reviewer false-accept 负例；当前错误产物不得进入正样本。
- 15 个有计划、external false 的 stagnant OTHER：可作为 recovery/correction 负例，生成成功
  continuation 后才能形成 preference pair。
- 37 个 plan unavailable：没有 RWKV action，不进入 RWKV state-tuning；只用于路由、熔断和
  durable resume 回归。

本轮可以作为数据种子，但应先修复 contract/evidence 标签生成器。否则把 21 个正确成品的控制器
误判直接训练进去，会教会模型重复修改正确文件；把 3 个 FP 标正则会固化错误结构。

## 可复核产物

- 机器摘要：`Round162_TYPED_CONTRACT_FULL90_GLOBAL_SUMMARY.json`。
- 临时只读聚合器：`temp/analyze_round162_full90_global.py`。
- 原始总表：`Round162_typed_contract_full90_20260823/results.json`。
- 每例证据：`Round162_typed_contract_full90_20260823/cases/<task_id>/audit.json`。
- 运行源码、配置与文件摘要：`Round162_typed_contract_full90_20260823/RUN_PROTOCOL.json`、
  `source_tree_manifest.json`。

本轮结论固定为：完整实验已完成，但架构未达标；不可替换 R126。下一步必须修 contract compiler、
typed evidence view 和 correction classification 三个共同根因，而不是继续对单例打补丁。
