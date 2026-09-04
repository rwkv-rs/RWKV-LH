# Selector 固定菜单与阶段 Scoped Harness 联动修复 R3 预登记

## 目的与冻结诊断

本轮只修复一个已由真实运行触发的全局架构缺陷，不评价或调整 state tuning。
修复前 R2 的 7 条完成结果和 11 份 audit 已原样保留；20/20 个 atom outcome
都在 Executor 请求前报出相同的菜单不等错误，Executor model request 与 action 均为 0。
R2 中止登记 SHA-256 为
`586f195448e5a5b639096fb96bda3eebcb4463f611f0ef736686e147b9bc75d0`。

根因是 `LongHorizonModel.__init__` 把两个不同层级的集合错误地要求完全相等：

- Selector 的 25 类全局分类空间必须固定，保证 2.9B hidden + MLP 的 class order、
  menu digest、head 和原始 logits 身份不变；
- 一个 planner atom 的 `ScopedAtomHarness` 必须只暴露该阶段被授权的最小工具子集，
  保证权限、写入根和副作用边界不被扩大。

因此正确不变量是子集关系，不是相等关系。

## 冻结整改语义

设 `G = NETWORK_EXACT_TOOL_LABELS - {ABSTAIN}`，设
`A = active Harness definitions + {final_answer}`：

1. 初始化只接受 `A <= G`；active Harness 出现任何不属于固定 Selector 协议的 operation
   时继续 fail closed。
2. 固定 25 类的名称、描述、顺序、menu digest、Selector 输入、state、MLP head、
   logits 和 raw argmax 均不得修改。
3. 不做 logit mask、重排、二次打分、top-k 回退、把未授权类别映射成第二候选，
   也不诱导 Selector 生成另一种原始结果。
4. 若 raw argmax 是当前 atom 未授权的全局 operation，保留完整 raw selection，记录
   `exact_tool_selection_rejected`，reason 固定为
   `operation_not_authorized_by_active_harness`；该次不得调用 Executor、不得执行 action。
5. Controller 可以依照既有协议发起一次新的 Selector 决策，但新决策必须有自己的
   selection/checkpoint/完整 raw logits，不能伪装为对上一结果的修正。
6. `ScopedAtomHarness` 的 operation order、权限过滤、写入根校验和 action transaction
   逻辑不变；strong planner 仍只 plan/review，不获得工具选择或执行权限。
7. 不修改、删除、隐藏或重排任何 RWKV 原始输出。

## 允许的代码范围

- `rwkv_lh/model.py`：把 active Harness 的严格相等校验改为未知 operation 校验。
- `tests/test_independent_network_selector_integration.py`：增加阶段子集、未知 operation、
  未授权 raw argmax 拒绝的回归测试。

不允许修改 Selector 服务、25 类协议、S60、G3/G6 state、vllm-rwkv、采样参数、
prompt、planner、Harness operation 定义、Full90 数据和验收口径。

## 固定验证顺序与门槛

1. 语法和定向单测：
   `uv run pytest -q tests/test_independent_network_selector_integration.py tests/test_network_exact_tool_selector_client.py tests/test_network_exact_tool_selector_protocol.py tests/test_rwkv_e2e_suite.py`。
2. 全部 Selector/Harness/contract-graph 同类测试必须通过；发现一条失败后扩展到完整
   同类文件，不做 case 特判。
3. 阶段子集初始化测试必须通过，并验证 Executor 只看到 active definition 加
   `final_answer`；Selector wire 仍看到固定 25 类名称和描述。
4. 未知 active operation 必须在初始化时 fail closed。
5. 未授权 raw argmax 集成测试必须同时满足：25 个 logits 原样保留、
   `postprocessed=false`、拒绝事件存在、该次 Executor prompts 增量为 0、action 增量为 0，
   且不得发生 operation 重映射。
6. 修复后先跑固定基本/只读/写入 canary，三类均必须越过初始化并产生真实 Selector
   请求；对应被授权选择才可产生 Executor 请求。
7. 再运行同一固定 Full90、同一参数、同一阈值和同一验证器，必须完成 90/90 调度；
   Full90 只用于组件与历史回归，不作为真实 Agent 能力等级。
8. 产品 18070 全程健康，实验只用物理 GPU0；实验 18075 与 Selector 29621 在结束后释放。

## 后续边界

只有本修复和相关回归通过后，才允许冻结新的真实端到端 Agent 能力阶梯，并据其失败簇
构建约 2000 条旧能力 state-tuning 数据。新能力基准与 Full90 分开编号、分开报告，
不得用基准题 literal、task id 或隐藏验收生成训练样本。
