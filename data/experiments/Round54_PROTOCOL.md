# Round54 预注册实验协议：RWKV-owned Ready-Task 原子细化

状态：在任何 Round54 代码修改和模型运行之前登记。

## 冻结基线与逐题证据

- 已上传最佳代码：`14d864d71bf670b479a33f4fdb63b4772b69d3c8`。
- Round46：Strict `31/90`、External `32/90`、Agent completed `55/90`、FP/FN `24/1`。
- Round53 同源 action reviewer：Strict `23/90`，已回退；完整人工报告见 `Round53_full90/MANUAL_BACKWARD_CAUSAL_ANALYSIS.md`。
- Round53 逐题共同根因：Task 常表示“全部文件/一批成员/递归发现/计算后写入/多阶段处理”，而 action contract 一次只能执行一个 Harness 调用。H12、H13、LH11 中，正确的下一个成员读取被当作“没有完成整个 Task”而拒绝；M01、M06、M18、H02、LH05 中，一个成员或 manifest 又被误当作整项 Task 完成。
- 正对照 LH02 将 15 个 checkpoint 分成 15 个单一 Task，Strict 通过。

## 唯一架构变量

在一个 `model_action` 类型的 ready Task 选择具体 Harness action 之前，增加一次 **RWKV-owned Task 原子性决定**：

1. RWKV 返回固定对象，`decision=execute|refine`。
2. `execute` 表示当前 Task 可由恰好一次后续 Harness action 产生足以判断其 postcondition 的 action result/effect；原 Task 不变，随后仍由 RWKV 选择完整 action。
3. `refine` 表示当前 Task 是集合、复合步骤、多阶段工作或抽象 effect；RWKV 返回一个最小 Task 子图和明确的 `completion_local_id`。每个子 Task 仍使用现有五字段 minimal Task contract，具体 action 仍在以后由 RWKV 单独选择。
4. Controller 只做通用图结构校验和 ID 分配：本地 ID 唯一、依赖存在、无环、根节点保留原 Task 的已完成依赖、`completion_local_id` 是唯一完成出口且所有子 Task 都是它的祖先。Controller 不拆 Task、不生成成员、不选择工具、不补 path/content/value、不改最终回答。
5. refine 后原 Task 通过现有 supersede 指针指向 RWKV 指定的完成出口；原 Task 的后继只有在该出口完成后才 ready。子 Task 也可再次由 RWKV判断并细化。
6. 一次最多 32 个子 Task、最多 8 个立即 ready 入口；只限制结构，不按标题、case、工具或答案筛选。

## 明确不改

- 不修改 Goal 解析、初始 Task DAG、Goal obligation extension、失败 recovery、post-action semantic commit、criterion evidence、final answer。
- 不增加 action reviewer、规则型工具选择、候选打分、答案改写或隐藏验收反馈。
- 不修改 Harness 工具实现、action 参数 schema、透明格式归一集合和采样参数以外的任何变量。
- 不读取 hidden acceptance、冻结 Codex 标准答案、case id 或 grader output 来决定 execute/refine 或生成子 Task。
- 请求数、token、延迟不作为本轮淘汰条件；只记录，不优化。

## 因果假设

1. 集合 Task 会先变成成员级 observation/producer Task，再由完成出口汇总，降低只处理第一个成员的 FP。
2. 一个 action 无法完成的“compute/sort/copy/verify whole set”不会再被错误地直接提交或完成。
3. 原 Task 的完成承诺转移到 RWKV 指定的子图出口，既保持已有后继 DAG，又不需要 controller 推断哪个子 Task最重要。
4. 已经原子的简单写入、单文件修复和一步观察应选择 execute，不能破坏 Round46 Basic 控制组。
5. 该变量不解决初始计划完全遗漏 producer、同源 expected/actual、action 格式错误；这些结果必须保持独立归因。

## 固定 Canary（运行前冻结）

| Case | 选择原因 |
| --- | --- |
| B01 | 最小原子写入控制，必须 execute 并保持 Strict。 |
| B02 | 读→派生 JSON 控制，检查已有原子 DAG 不被破坏。 |
| B10 | 单文件 coding 闭环控制。 |
| M03 | 中等迁移控制。 |
| M12 | 正确单次代码写入不能被误细化/阻断。 |
| LH02 | 15 个已原子 checkpoint 的 hard 正对照。 |
| M01 | 多 service 集合任务。 |
| M06 | 多文件 copy 与 manifest。 |
| M16 | primary/fallback 成员集合。 |
| M18 | 递归多文件 digest。 |
| H02 | 20 shards 聚合。 |
| H12 | 15 shards 的单 Task。 |
| H13 | 24 文档按 4 个一批的 Task。 |
| LH11 | 40 artifacts 按 8 个一批的 Task。 |
| LH01 | 初始计划遗漏 producer 的反对照；本变量不应被误归因为解决。 |

## 固定验证

1. 单元测试：execute 保持原 Task/后继不变；refine 完整子图按 RWKV指定出口 supersede；根依赖保留；所有节点必须到达出口；未知依赖/环/非唯一出口/超过 ready 上限拒绝；Controller 不生成语义字段。
2. 完整 offline suite、LH-Control `30/30`、catalog validate-only `90/90`、31 文件确定性架构验收。
3. 固定 Canary 只用于诊断 atomicity decision、子图和控制组，不替代 E2E-90。
4. 完整 E2E-90：`--suite all --max-transitions 200 --concurrency 8`。
5. 运行固定 analyzer 后，逐题检查全部 90、全部 Round46 outcome 变化、FP/FN、每次 refine 子图和未细化的集合 Task。

## 保留与上传门槛

- Strict `>31/90`；
- FP `<=24`、FN `<=1`；
- Basic/Medium/Hard 完整报告；
- offline、LH-Control、catalog、31 文件回归全部通过；
- raw/delivered final output 字节一致；
- 无 case 特判、无 controller Task/action/答案选择或修改。

未满足则回退 Round54 源码/测试，只保留实验协议、原始数据和人工分析，不上传为最佳架构。
