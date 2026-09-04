# Round52 预注册实验协议：严格单层因果 Frontier

状态：在任何 Round52 代码修改和模型运行之前登记。

## 冻结基线与证据

- 已上传最佳代码：`14d864d71bf670b479a33f4fdb63b4772b69d3c8`
- 已上传完整基线 Round46：Strict `31/90`、External `32/90`、FP/FN `24/1`
- Round50 两阶段候选：Strict `6/90`
- Round51 两阶段 + tool_name 别名：Strict `17/90`
- Round51 后源码/测试已回退，完整 offline `364/364`
- Round46/Round50/Round51 逐题反向分析共同显示：RWKV 在同一 Task batch 中预编未观察的未来依赖链，产生抽象“排序/计数/验证/完成”Task、猜测路径、集合 cardinality 错配和 observation→arguments 丢失。

## 唯一架构变量

对正常 forward planning 的两个入口实施同一个结构不变量：**一次 Task batch 只能描述一个全部立即可执行的因果层**。

1. Initial plan：每个 Task 的 `dependencies` 必须精确为 `[]`；不得引用同批 local id。
2. Goal-obligation extension：每个新 Task 只能依赖 state 中 active+completed 的既有全局 Task ID；不得依赖同批新 local id。
3. 每批仍最多 8 个立即可执行 Task，Task schema 仍是原五字段，具体 action 仍由后续 RWKV 单请求选择。
4. 第一次违规时使用原有第二次协议纠正机会；第二次仍违规则 fail closed。

该变量只把已存在于 prompt 的“next executable causal frontier”变成可验证协议约束，不生成 Task、不删除某个候选、不选择 action、不补参数、不判断答案。

## 明确不改

- 不修改 single-request G1i action commitment、透明格式层、Harness 工具目录、参数 schema 或采样参数。
- 不修改 recovery replan；失败替换链留作独立实验。
- 不修改 Goal/criterion/evidence/Task postcondition verifier、最终答案和 external acceptance。
- 不根据 hidden acceptance、冻结参考答案或具体 case 名称筛选 Task。
- 不由 controller 合并、排序、改写或选择 RWKV Task；整批只做结构接受或整批拒绝。

## 因果假设

1. 读取/列举层完成后，下一次规划可以看到真实内容/路径，再生成 producer Task，降低猜测参数与错误工具。
2. producer 自动 snapshot 后，Goal evidence 有机会直接完成，减少多余 read/verify/noop Task。
3. 集合任务每轮只能基于已观察 member/page 继续，降低“一项当全体”和游标重复。
4. 代价是 planning 请求增加；本轮效率不作为 gate。

## 固定验证

1. 单元测试：initial local dependency 拒绝、obligation local dependency 拒绝、completed existing dependency 接受、pending/failed existing dependency拒绝、整批不被部分选择。
2. 完整 offline suite、LH-Control `30/30`、catalog validate-only `90/90`、31 文件确定性架构验收。
3. 固定真实 canary 只用于诊断：覆盖此前多余验证、集合、fallback、FP 和长链 case；不替代全量。
4. 固定 E2E-90：`--suite all --max-transitions 200 --concurrency 8`，输出 `data/experiments/Round52_full90`。
5. 运行固定 analyzer，与 Round46 已上传最佳比较；逐题检查全部非 Strict、全部 outcome 变化、所有 FP/FN。

## 保留与上传门槛

- Strict `>31/90`；
- FP `<=24`、FN `<=1`；
- Basic/Medium/Hard 完整报告；
- offline、LH-Control、catalog、31 文件架构回归全部通过；
- raw/delivered RWKV final output 原政策下字节一致；
- 无 case 特判、无 controller Task/action/answer 选择。

未满足则回退 Round52 源码/测试，保留实验数据和分析，不上传为最佳架构。
