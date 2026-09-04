# Round158 Contract Graph Full90 诊断分析

日期：2026-08-23

## 结论

本轮完整运行 RWKV-E2E-90，最终 `TP=34 / FP=9 / FN=4 / OTHER=43`。新架构把
Round148 的 GPT logical calls 从 521 降到 344，并把 FP 从 16 降到 9；但 strict TP
从 41 降到 34，低于 R126 canonical 的 36，且出现 2 个非终态 `running`。因此本轮不通过
晋级门，不能替换 R126，也不能标记为 Full90-ready。

当前能力边界很清楚：基础层可严格完成 `24/30`，适合窄范围、精确创建/复制、简单读取与
结构化写入；需要复杂 schema 保真、多源组合、递归聚合、代码修复、崩溃恢复或长依赖时仍不
可靠。中转站故障是重要损失源，但不是全部根因。

## 固定产物与完整性

- 协议：`Round158_CONTRACT_GRAPH_FULL90_DIAGNOSTIC_PROTOCOL.md`。
- 原始目录：`Round158_contract_graph_full90_20260823/`，约 235 MiB。
- 90/90 均写入 `results.json` 和逐例 audit；runner/verifier infrastructure failure=0。
- 状态：completed=43、interrupted=45、running=2。M15、M23 因 scope validation 异常
  逸出而缺失 terminal causal event，完整性门失败。
- 源码、参数、数据来源和 SHA-256：运行目录中的 `RUN_PROTOCOL.json`、
  `source_tree_manifest.json`。运行时间由 02:46:34 UTC 至 05:22:30 UTC，约 2h36m。
- 运行前 159 项单测通过；RWKV 和 Supervisor 配置模型健康检查通过。

## 预注册指标

| 指标 | 参考门 | Round158 | 结果 |
|---|---:|---:|:---:|
| Strict TP | >36 | 34 | FAIL |
| FP | <=24 | 9 | PASS |
| FN | <=1 | 4 | FAIL |
| 90 例持久化 | 90 | 90 | PASS |
| running | 0 | 2 | FAIL |
| B strict | >=23 | 24 | PASS |
| M strict | >=10 | 9 | FAIL |
| H strict | >=2 | 1 | FAIL |
| LH strict | >=1 | 0 | FAIL |

完整分类：

- B：TP24 / FP1 / FN1 / OTHER4。
- M：TP9 / FP7 / FN1 / OTHER13。
- H：TP1 / FP0 / FN1 / OTHER16。
- LH：TP0 / FP1 / FN1 / OTHER10。
- byte-precision 参考例 B01/B06/B13/B19/B28 为 4/5；B13 丢失未要求修改的
  `deployment.enabled`。

与固定对照相比：

| 轮次 | TP | FP | FN | OTHER | GPT logical | GPT tokens | RWKV actions |
|---|---:|---:|---:|---:|---:|---:|---:|
| R126 canonical | 36 | 30 | 0 | 24 | - | - | - |
| Round148 atom graph v4 | 41 | 16 | 2 | 31 | 521 | 3,309,497 | 624 |
| Round158 contract graph | 34 | 9 | 4 | 43 | 344 | 4,506,270 | 560 |

相对 Round148，logical calls 减少 34.0%、actions 减少 10.3%，但 total tokens 增加
36.2%。每个 strict TP 的 logical calls 从 12.71 降到 10.12，而 tokens 从 80,719 增到
132,537。调用次数方向正确，累积 result capsules 和重复 correction 使 prompt 成本反向恶化。

## 中转站故障簇

- 65 个 Planner reasoning fallback 事件，覆盖 59/90 cases；说明大量 medium 请求先收到 5xx。
- 27 个 `supervisor_call_failed` 事件，覆盖 26 cases。
- 26 cases 最终为 `contract_plan_unavailable`，全部 0 RWKV action；这 26 例单独贡献
  26 个 OTHER。
- GPT logical/physical/returned = 344/451/319。物理请求比逻辑请求多 107 次；成功返回
  前后的失败物理尝试形成显著延迟和不稳定性。
- 排除这 26 个零计划 case 后，观察到的条件 strict 为 34/64=53.1%；该数字不能当作
  “中转修好后的反事实分数”，因为故障集中在运行后段和复杂题，样本不是随机缺失。

中转不稳定解释 26 个 OTHER，但不解释 9 FP、4 FN、17 个非传输 OTHER。

## 架构自身缺陷

### 1. Reviewer 假接受：9 FP

所有 FP 都有足够的最终 artifact observation，但 Reviewer 仍判 satisfied；Full90 的 151 次
review 中 deterministic veto 触发为 0，现有机械内核覆盖面过窄。

- 精确模板/跨源组合：M04 标题漏 version；M14 标题漏 version 且 date label 错。
- 排序/精确字节：M08 把 `worker` 排在 `web` 前且漏末尾 newline。
- schema/key/container：B25 把源键 `runtime` 改成 `nested`；LH06 用 `source_path` 而非
  `source` 并回显不可信目标；M26 多出 `source_record` 且 index 错；M29 缺少
  `translations` 容器。
- 计算：M18 digest map 错；M19 `/items` 计数少 1。

根因不是 Reviewer 看不到结果，而是 prose obligation 没有编译成可执行 predicate；让另一
次 LLM review 重读同样 evidence 不能稳定解决。

### 2. 正确成品无法收口：4 FN

M05、H04、LH10、B21 的 external checks 全通过，但系统因 evidence stagnant 中断。典型模式
是 artifact 已正确，RWKV 的 `check_command` 参数或形式化验证动作失败，Reviewer 随后要求
重复 verification。4 个 FN 消耗 36 GPT logical calls、505,607 tokens 和 44 actions。

用户要求“verify”不应自动等价于必须成功执行任意 shell command。最新 artifact 的 typed
read/digest/local predicate 已能闭合时，应由本地 verifier-style checker确认；GPT 只处理剩余
不可计算语义。

### 3. correction 不收敛：15 个预算/停滞 OTHER

- evidence stagnant 的 OTHER=14；patch budget exhausted=1（LH03）。
- 18 个 stagnant cases（含 4 FN）消耗 2,333,466 GPT tokens；LH03 单例再消耗
  432,366。两类没有产生 strict TP，却占本轮 GPT tokens 的 61.4%。
- 典型失败：B10 多次修 `import re` 但 replace 无效；B22 重复输出普通 bullet；B13
  重写 JSON 丢字段；B24 丢行内字段；M24 tie-break 排序仍错；长代码链 H01/H11/LH01
  反复修补但不通过；恢复任务 H08/H17/LH04 schema 与 resume 语义均不收敛。

当前 correction policy 只检测 evidence digest 停滞，未判断“错误签名和操作策略是否变化”。
Planner 常追加同一种失败 operation，导致重复 GPT/RWKV 调用。

### 4. scope 与生命周期：2 个 running

- M15：递归 list 已发现 `docs/nested`，后续读节点仍被 scope validator 判为未授权。
- M23：用户要求创建完整 `dist/` tree，correction 中创建 `dist/config` 被判为未授权。

scope policy 没有表达“用户授权根的后代路径”和“由可信 list/read 结果发现的路径”。异常又在
部分 graph/action 已提交后逸出，没有统一 `run_failed`/`run_interrupted`，留下 running。

### 5. 架构完整性中已经成立的部分

- GPT tool execution=0；RWKV 仍是唯一操作主体。
- completed Final 全部与 raw RWKV candidate byte-exact，controller/reviewer 未改写答案。
- revision 0 后新增 obligations=0，frozen contract 生效。
- 537 个 atom outcome 都至少执行 1 个 action；0-action 自述证据问题已消失。
- 43 个 completed cases 各有一个 finalizer；无 zero-action finalizer。
- 35 cases 存在真实 atom 时间重叠。

## 更合适的下一版架构

1. **Strong Planner plan-once。** Planner 输出 typed obligation IR：路径、JSON schema、保留字段、
   排序 key、精确模板、公式、hash/line/byte 算法和排除规则。不要只给 prose predicate。
2. **RWKV 小事务执行。** 把 single-operation atom 提升为窄 scope 的 2–4 action transaction，
   在同一 RWKV state 内完成 `read -> transform/patch -> read/check`。工具权仍完全属于 RWKV，
   强模型不生成业务内容或工具参数。
3. **Local predicate first。** 本地 checker 只做由 typed contract 明确给出的确定性比较和 veto；
   不看 hidden acceptance、不替代 RWKV 执行。精确内容已经闭合时不再调用 GPT Reviewer。
4. **GPT Reviewer exception-only。** 只有剩余义务不可机械计算、或出现新的矛盾类型时调用；
   Reviewer 只看每个 artifact/obligation 的最新有效视图和必要因果引用，不重传完整 capsule 历史。
5. **Correction signature。** 对 `(unsatisfied obligations, latest errors, latest artifact hashes,
   proposed operation kinds)` 取摘要；重复签名不得再问 GPT 或执行同构 patch，应切换 operation、
   交给 RWKV recovery transaction，或安全终止。
6. **可靠路由。** 使用 phase-specific primary/fallback、熔断和已提交 plan 缓存；一个中转 5xx
   不能让 0-action case 直接结束。模型选择必须通过真实 Planner/Reviewer canary，不能只看
   `/models` 或简单 JSON probe。
7. **终态与 scope。** 所有异常统一提交 terminal event；scope 支持用户声明根的后代创建，
   以及依赖链上可信 discovery 结果引入的路径，且整张 patch 应在提交前完成 DAG-aware validation。

## 作为 state-tuning 数据的使用方式

- 34 TP：在 external checks、raw Final、action/result refs 全一致后，可作为正种子；优先提取
  短事务和 state handoff，不直接训练 GPT 文本。
- 9 FP：作为 Reviewer false-accept 和 RWKV schema/计算错误的负例；必须保留 expected-vs-actual
  差异，不得作为正样本。
- 4 FN：artifact 是正目标，失败的 verification/correction 决策是负例，适合训练“何时停止”和
  “内容证据已经充分”。
- 17 非传输 OTHER：适合做 recovery/correction 对比数据；只有人工或机械构造出成功 continuation
  后，才可形成正对。
- 26 transport OTHER：只用于路由/重试/熔断回归，不进入 RWKV 能力训练集。

本轮找到了可用的数据种子，但不能直接把全部轨迹混合训练；必须按上述标签和证据门筛选。

