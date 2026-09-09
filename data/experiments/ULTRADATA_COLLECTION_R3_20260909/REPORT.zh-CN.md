# ULTRADATA_COLLECTION_R3_20260909：审计修复后的真实链路

Agent：固定三题 **Strict 0/3、completed 0/3、mutation 0、动作 2**。第一题 `strong_stage_checker_unavailable`、第二题 `strong_planner_unavailable`，均保留 running/pending 的可恢复中断；第三题 `protocol_rejection_budget_exhausted`，状态 blocked。总墙钟 335.93 秒。没有完成整题，不能声明闭环完成。原始结果、分母、预算和源码在运行及抽取期间保持冻结，没有重评分 R1/R2。

角色：Planner `gpt-5.6-sol` 三次请求、两次计划接纳、一次 HTTP 500；Stage Checker 两次请求、一次 advance、一次 HTTP 500。两个失败请求各经历客户端两次 HTTP 尝试。Selector 2.9B 八次交接 / 24 次菜单求值；Executor 13.3B 十四次生成，Step Auditor 两次生成；Finalizer 和 Final Auditor 未到达。所有 RWKV 角色独立 zero，optimizer steps 仍为 0。

## 冻结与验证

运行源码为 `21ebbaa9`，已通过审计合同修复轮完整回归 **1162 passed、0 skipped、175.93 秒**；本轮没有修改生产、测试或依赖，沿用该完整测试。日志 `../AUDITOR_EVIDENCE_CONTRACT_R1_20260909/FULL_TESTS.log`，SHA-256 `4533ee4500b3afadfb5a159ac00e53f70ab9d384b9ecc82e175fb9026cebd261`。

运行前重新核对服务器 engine 6395 个文件、Selector 项目 118 个文件、Native 项目 132 个文件，以及两个实际模型权重。服务 PID 和工作目录符合冻结清单；服务器没有使用 Git。两份 attestation 及启动绑定见 `REMOTE_ATTESTATION.json`、`EXECUTOR_SOURCE_ATTESTATION.json`、`DEPLOYMENT_BINDING.json`。

题目、模型、zero State、三菜单、每题 200 transitions / 1200 秒、原 Selector scope 和数据阈值沿用原登记。Planner 输出上限 8192、Stage Checker 2400、Executor 1800、Step Auditor 400 tokens。本轮 RWKV 的 16 次实际生成均自然 stop；没有因输出 token 截断而终止。第三题的“预算耗尽”是连续协议拒绝累计到 12，两个 HTTP 500 是服务请求失败，二者不可混称输出预算不足。

通过唯一角色 builder 重建两次真实 Step Auditor 输入，与运行时记录的 prompt SHA 逐字节匹配。候选抽取完成后再次核对全量生产源码清单。原始输入、输出、工具资格、参数拒绝及请求错误见 `CONTRACT_COMPARISON.json`、`SUMMARY.json`；完整 SHA 清单见 `EVIDENCE_SHA256.json`。

## 审计修复实际生效到哪里

第一、三题各执行一次 `list_directory`，空目录观察成功且完整。两个 Step Auditor 均原样返回 `continue`、`evidence_refs=["A00001"]`、`gaps=[]`，完成 S1。没有 Controller 改写裁决，也没有依赖矛盾校验强迫继续；本轮没有审计协议重试。R2 的“完整空目录却持续报告 root-unproved”在这两个边界未复现。

第一题随后阶段检查连续收到 HTTP 500，记录 pending 后中断；第二题初始 Planner 同样失败，没有产生计划或角色调用。这是已确认的远端 HTTP 状态，不能进一步推断网关内部失败原因，也不能解释成 Planner 不愿输出或本地 parser 拒绝。

第三题的阶段检查原样返回 advance，确认完整空目录足以满足本次起始观察标准。随后进入 S2 / mutate，说明 trace 已越过旧卡点。本轮仍只观察了两个 Step Auditor 边界，不代表所有步骤或 Final Auditor 的语义质量已验证。

## 第三题：设置的标准与真实输出

公开任务要求交付标准库 Python `main.py`，从 stdin 读输入并输出答案。S2 要求创建完整实现，write root 为 `main.py`。此时它确实不存在；下面只使用生产可见事实，没有读取私有验收或参考实现。

| 交接 | 当前合同 | 真实输出 / 行为 |
| --- | --- | --- |
| Planner → Controller | S1 观察后，S2 创建完整实现 | 计划被接纳，S1 完成且阶段检查 advance |
| Controller → Selector | mutate 家族按结构性工具前提筛选 | `main.py` 的类型为 missing，却仍给出 copy_file / move_file；现实现只检查 destination |
| Selector → Executor | 选择一个具体操作，Executor 只能填写该工具参数 | 六次选中 move_file，选择输入摘要均为 `2b78153900f11dbf7c9ff3f86928492f9f6999c5139660c0e0b04d17b7761d82` |
| Executor → 执行前校验 | move_file 的 source 必须是现有文件 | 十一次提交 source=main.py、destination=main.py，被拒绝；另外一次生成了内部 action-commit 名称而被 parser 拒绝 |
| 拒绝 → 同角色重试 | 每次选择可再修参数一次 | 该次 Executor 收到错误，但无法为不存在的源文件补出有效参数 |
| 参数重试耗尽 → 新选择 | 新选择应能看到相关失败事实 | 当前 Selector 的进度只含执行动作和审计语义反馈；参数未执行，不形成 last_action，拒绝原因也未传入，故输入未变 |
| 停止 | 资源上限只能中断或阻塞 | 累计 12 次协议拒绝后 blocked；没有真实文件变更，没有重新调用 Planner |

可复核根因有两项：

1. `stateful_goal_loop.py:633` 的多参数操作资格检查选用 destination；同文件 `:787` 的执行前校验却遍历 source 和 destination，且错误里的 compatible_targets 仍只有 destination 候选。这是所有复制/移动场景共享的合同缺口。整改应按参数职责和完整/未知的发现范围判断可行性，同时保留从目标范围外合法读取源文件的能力，不能通过某个文件名、后缀或把“未发现”等同“不存在”来删工具。
2. `stateful_goal_loop.py:850` 的参数重试用完后重新选择；`:396` 和 `:2433` 的反馈路径只把审计语义缺口交给 Selector，action 协议拒绝的 feedback 为 null。因此重选不携带刚发生的参数/工具适用性失败。本轮六次相同输入及 12 个拒绝事件证明了放大链。整改需要明确“参数可以修复”与“重新选择所需的失败事实”，保持同一步和因果身份；不能把它误转为计划错误。

这两项是本轮发现的待修工程问题，尚未通过新修复和回归。预算 12 正确阻止无限重复，但它不是问题根因；单纯加大预算不会让原封不动的 Selector 输入得到新证据。现有五角色分工无需因此更换；Native 跨角色 checkpoint 前置依赖及三菜单成本也没有在本轮整改或消融。

## 当前 Selector 数据缺什么

唯一抽取器得到六条自动标注候选，来自两个成功观察边界各三个菜单；均为 train，dev / confirmation 均为 0。完整服务器 token 证据为 6/6。另 18 条创建阶段错误选择进入独立复核队列，未伪造成功动作或自行纠正标签。整个候选集仍为 invalid。

预注册要求至少 30 条已核验菜单行、十个不同边界，覆盖 py_root / mutate / execute / missing_target，并具有非空固定切分。本轮自动样本仍只覆盖 directory_root / directory_target；后续错误边界虽已发生，但未经独立纠正不能算已核验覆盖。跨切分相似度检查没有违规是因为没有跨切分可比样本，不代表已证明数据独立性。

当前阻止正式训练的是 Selector 的标签、数量、覆盖与固定回归条件；不是要求 Finalizer 先运行，也不是要求 Agent 先高分。三个固定来源家族本身的切分为 train / dev / train，没有 confirmation，反复跑相同三题无法填补这个来源缺口。后续需要有区分度的实际生产边界和预先登记的新增来源；不得修改家族名或切分算法来凑通过。

本轮没有新建正式 `data/datasets/` 版本、没有启动优化器、没有访问 Holdout。原始大 trace 与候选文本留在本地，Git 保存必要对照、清单和报告。HTTP 500 不通过本地吞错或回退 13.3B Planner 掩盖；未完成链路如实保留。
