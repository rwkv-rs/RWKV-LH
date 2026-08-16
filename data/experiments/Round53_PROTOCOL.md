# Round53 预注册实验协议：RWKV 动作执行前语义复核

状态：在任何 Round53 代码修改和模型运行之前登记。

## 冻结基线与依据

- 已上传最佳代码：`14d864d71bf670b479a33f4fdb63b4772b69d3c8`
- Round46：Strict `31/90`、External `32/90`、Agent completed `55/90`、FP/FN `24/1`
- Round52 严格单层 frontier：Strict `3/90`，已回退。
- Round46、Round51、Round52 的逐题反向分析共同显示，最早的可执行错误高频发生在 Task→Action 边界：copy Task 写 manifest、read/verify Task 执行 mutation、run-tests Task 写文件、多文件 Task只处理一个成员、依赖 observation 已存在但 write 参数仍是占位符或猜测值。
- 当前 postcondition check 位于副作用之后。它即使拒绝错误，也可能已经损坏 artifact；且 recovery 经常重复错误变量。

## 唯一架构变量

在一个完整、已通过现有 G1i schema 校验的 RWKV action 真正执行之前，增加一次 **RWKV-owned semantic review**：

1. Reviewer 只看到 immutable Goal、active Task、最新 dependency/action capsule、当前 workspace manifest metadata 和该完整候选 action。
2. Reviewer 返回固定三字段对象：`schema_version`、`decision=accept|reselect`、`reason`。
3. `accept`：原候选 action 原样进入 Harness。
4. `reselect`：原候选整项丢弃；把 RWKV 自己的 reason 和原候选作为只读反馈，再由 RWKV 重新生成一个完整 action。Controller 不选择工具、不改参数、不从多个候选中排名。
5. 最多三次完整候选。三次均未被 RWKV 接受则 fail closed。
6. reviewer 只能判断 active Task 与 action 是否语义一致、是否使用了已有观察、是否是一项可执行进展；不得生成替代 action、参数、expected answer、Task、criterion 或最终答案。

该变量只移动语义检查到副作用之前，并把重新选择权留给 RWKV。它不通过规则推断哪个 action 正确，也不改写 RWKV 的最终答案。

## 明确不改

- 不修改 initial Task DAG、Goal obligation extension、recovery replan、Task/Goal evidence、Harness 工具和参数 schema。
- 不修改现有透明格式归一化集合。
- 不读取 hidden acceptance、冻结 Codex 答案、case id 或 grader output。
- 不增加 controller 基于标题关键词的工具白名单/黑名单，不自动补 path/content/value。
- 不从多个 RWKV action 中以规则打分选优；候选按生成顺序由 RWKV reviewer逐个 accept/reselect。
- 不以请求数、token 或延迟作为本轮淘汰条件。

## 因果假设

1. mutation/verification 角色错位会在副作用前被 RWKV 自己识别，减少 artifact 被验证 Task 二次破坏。
2. reviewer 同时看到 Task、依赖 observations 和完整 action，可发现 manifest 代替 copy、空 aggregate、占位符 content、错误路径等明显不一致，并要求 RWKV 重选。
3. 保留完整 DAG，因此不会复现 Round52 把有效 first frontier 整批丢弃的问题。
4. 不能解决 initial plan 完全遗漏 producer、集合展开、Goal evidence 假阳性；这些保持为后续独立变量。

## 固定验证

1. 单元测试覆盖：accept 原 action 字节/对象不变；reselect 后仅使用 RWKV 新 action；reviewer 不得返回 action/arguments；三次 reselect fail closed；review protocol correction；事件完整记录 raw candidate、decision、reason、最终 candidate。
2. 完整 offline suite、LH-Control `30/30`、catalog validate-only `90/90`、31 文件确定性架构验收。
3. 固定真实 canary 只诊断 copy、Markdown、run-tests、集合和 API role mismatch，不替代全量。
4. 完整 E2E-90：`--suite all --max-transitions 200 --concurrency 8`。
5. 固定 analyzer 后逐题检查全部非 Strict、全部 Round46 outcome 变化、FP/FN 和所有 pre-action reselect。

## 保留与上传门槛

- Strict `>31/90`；
- FP `<=24`、FN `<=1`；
- Basic/Medium/Hard 完整报告；
- offline、LH-Control、catalog、31 文件回归通过；
- raw/delivered final output 继续字节一致；
- 无 case 特判、无 controller action/answer 选择或修改。

未满足则回退 Round53 源码/测试，保留本地实验数据与分析，不上传为最佳架构。
