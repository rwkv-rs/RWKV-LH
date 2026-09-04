# G1J Selector Head v2 全链路诊断结果

日期：2026-09-04（Asia/Shanghai）

## 最终结论

当前系统 **不能作为可靠 Agent 发布**。控制链中的确定性工程缺陷已经修复，但固定真实 canary 仍未通过：修复 Selector 权限后，2.9B Selector Head v2 在第一个纯读取步骤直接以 `0.8518835041612606` 的置信度选择 `ABSTAIN`，而 `read_file` 的 logit 只有 `0.4133441150`。这是当前 Selector Head/训练分布的能力缺陷，不是工具不存在、身份缺失、格式失败、上下文过长或状态未保存。

同时，隔离 Selector 后的原生 13.3B Executor 反事实表明：即使第二轮输入已经明确给出 `missing_read_roots=["verify_project.py"]`，Executor 仍重复读取已经成功读取过的 `pricing.py`。后续 E1–E5 输入消融修正了本报告最初的过早归因：短单一状态输入可使相同 13.3B 在读取矩阵达到 18/18，但生产完整事实输入仍会重复旧路径。因此当前结论是“输入合同与 zero-State 能力共同受输入分布影响”，不能只归为模型能力，也不能宣称工程输入已经解决。完整修正证据见 `../RWKV_EXECUTOR_INPUT_CONTRACT_V5_20260904/RESULT.md` 与 `../RWKV_EXECUTOR_INPUT_CONTRACT_V5_20260904/R5_CONTROLLER_COUNTERFACTUAL_RESULT.md`。

这些证据不能推出“RWKV 架构本身能力不好”；能够推出的是：**当前 2.9B Selector Head v2 和当前 13.3B zero-State Executor 配置尚不足以完成真实 Agent 链路。** 本轮没有执行 StateTune。

## 缺陷分类

| 层 | 缺陷 | 归类 | 状态与证据 |
|---|---|---|---|
| Stateful Goal | 机械证据不完整时没有应用已有的相同失败/相同只读零进展预算，导致 120 次 action 和 489 MiB SQLite 放大 | 工程缺陷 | 已修复。相同失败第 5 次、相同只读零进展第 3 次可恢复阻断，不再打开新的 audit boundary |
| Planner frontier | 没有 `write_roots` 的纯读取步骤仍允许 `run_command`，因为只过滤了 `workspace_mutation`，漏掉 `local_process_mutation` | 工程缺陷 | 已修复为依据统一 `side_effect` 字段过滤全部副作用 operation |
| Selector 权限 | Strong Planner eligibility override 丢掉固定协议标签 `ABSTAIN`，把 Head 的全局 argmax 屏蔽后强迫选低置信错误工具 | 工程缺陷 | 已修复。普通 action frontier 始终保留 `ABSTAIN`；终局仍只允许 `final_answer` |
| 协议计数 | 合法的 Selector `ABSTAIN` 会被当成 Executor/action 格式拒绝，可能错误累计到 12 次协议失败 | 工程缺陷 | 已修复。现在零 Executor 请求、零 action、零 protocol rejection，并以 `selector_abstained` 阻断 |
| Executor 局部状态 | Controller 已有机械 gap，但 Executor 的 `goal_frontier_assignment` 未携带当前 assigned/successful actions 与 missing roots | 工程缺陷 | 已修复。局部事件现在携带 Controller 的既有机械证据，不新增模型调用或完成权限 |
| 2.9B Selector Head v2 | synthetic dev 为 1.0，但真实中文多工具纯读取 frontier 首次选择 `ABSTAIN` | 当前模型/角色能力缺陷 | 未解决；固定 canary 证实 Head v2 不可发布 |
| 13.3B Executor | 短单一状态输入可正确遵循 remaining root，但生产完整事实输入仍再次填写 `pricing.py` | 输入合同/zero-State 输入敏感性，尚不能单因归类 | 未解决；E4 18/18，E5 33/42，R5 真实链路仍失败 |
| RWKV 基础架构 | 是否存在不可训练的根本能力上限 | 尚不能归因 | 当前证据只能评价具体 Head、数据分布和角色配置，不能据此否定 RWKV 本身 |
| 推理引擎 | native State 续接、模型/Head 身份、token 上限或协议传输是否损坏 | 未发现运行时缺陷 | 服务身份和 native recurrent transport 可验证；Executor 每个 action 为独立原生 State session；实际 token 远低于 16,384 |

## 固定全链路结果

### 1. 原始 Head v2 canary

- 固定用例：`AGENT-LADDER-L1-FIX01`，Strong Planner、2.9B Selector、13.3B Executor、zero State、progressive disclosure。
- Planner 正确创建 S1：读取 `pricing.py` 与 `verify_project.py`，随后修复、更新 README、运行验证；Planner 没有把“声明要读取”当作已完成证据。
- 120 个 action 全部停留在 `S1@1`，0 个完成 step，0 次协议拒绝；54 次相同 `read_json` 失败后又出现 38 次相同 `run_command` 失败。
- Selector 使用同一个 `(step_id, revision)` State 链，120 轮 token position 达到 137,412；SQLite 达 489 MiB。State 确实在更新，问题是错误选择被无限放大。
- `results.json` SHA-256：`8c395ea7e866597d0d6b04073d28ebc081e1230ed04d09208794562ed0db0075`。

### 2. 停滞预算修复后

- 8 个 action 后按既有预算阻断：`date_diff ×1`、`run_command ×2`、`check_command ×5`。
- 0 次协议拒绝，说明所谓“12 次 action 协议失败”不是这次真实轨迹的格式现象。
- Selector State 从 token position 1,479 增长到 10,116；8 个 Executor session 的最大输入约 2,527 tokens，远低于 16,384。因此不是 token 截断或未闭合 Markdown 代码围栏造成。
- 8 次 Executor 原始 `{name,arguments}` 调用均由 `direct-call-envelope.v3` 正常化为 `{function,params}` 并通过结构协议。Markdown 开放围栏是生成锚点，不是协议失败根因。
- `results.json` SHA-256：`78683c1c9522c763ccf79d48de20c94008c99aef14096ca0732d077c06c92a3d`。

### 3. Selector frontier 权限修复后

- S1 可选集合为 `list_directory, search_text, read_file, read_json, file_digest, bind_evidence, check_command, calculator, date_diff, current_time, ABSTAIN`；有副作用的 `run_command` 已移除。
- 第一次 Selector 原始 argmax 是 `ABSTAIN`，置信度 `0.8518835041612606`；`read_file` logit 为 `0.4133441150`。
- Controller 立即以 `selector_abstained` 阻断：0 Executor 请求、0 action、0 protocol rejection。
- `results.json` SHA-256：`c023eae31929c12295454f8b3d5429d67076e4a61f456b56384d49643c5fdd14`。

这个结果排除了“工具不存在”和“缺少身份”：`read_file` 在 Head 固定 25 类、服务菜单和该步 eligibility 中均存在；服务模型、权重、Head、协议与 feature 身份均已绑定。错误发生在存在合法选择的情况下，Head 把真实输入判为 abstain。

## Selector 能力归因

Head v2 的 400 个 train/dev feature 在固定合成数据上达到 1.0，但训练只有英文、两轮、模板化的 persistent sequence；线上是中文任务、Strong Planner frontier、多工具竞争和更长的真实因果轨迹。训练序列总 token position 为 1,292–2,225；线上第一次选择在 1,455（仍在训练范围内）就已经错误，后续轨迹还会超过训练最大值。因此：

1. 不是“State 没更新”：state scope、父 checkpoint、digest 和 token position 都连续增长。
2. 不是单纯“2.9B 参数量必然不够”：当前实验没有将基础模型与代表性训练/评测分离。
3. 已证实的是 Head v2 的合成分布不能泛化到真实 Planner frontier；在有 `read_file` 的明确步骤选择 `ABSTAIN`，当前 Head 不具备生产工具选择能力。

后续若训练新 Head，必须先冻结代表性真实轨迹评测，再比较 zero-State 与 StateTune；不能直接用 StateTune 覆盖此诊断。本轮未训练或加载任何 StateTune。

## Executor 能力归因

固定反事实用诊断 Selector 强制两次选择 `read_file`，只隔离 13.3B 参数填写；它不计入产品通过率。

- 修复前，第二轮 Executor 已收到第一次 `pricing.py` 的完整 action/result，但没有收到 Controller 已算出的机械 gap；两轮均生成 `pricing.py,start_byte=0,max_tokens=4096`。
- 修复后，第二轮明确收到 `assigned_action_ids=["A00001"]`、`successful_action_ids=["A00001"]`、`missing_read_roots=["verify_project.py"]`、`completion_preconditions_satisfied=false`、`completion_authority=false`。
- 修复后输出仍完全相同，0 次协议拒绝，前后原始结果 SHA-256 都是 `2d0ffac6944b74333d943f192ad529f593a6c0c6f9b5a566771c9023be3ccb78`。

Selector 只选 operation、Executor 只填参数的职责边界仍然成立，但不能据此判定当前 Executor 输入设计已经正确。E4 证明同一 zero-State 13.3B 在 377-token 单一状态输入上可以稳定遵循 remaining root；E5 跨类为 33/42；R5 生产输入虽已把 remaining state 放到尾部，仍因完整 supporting fact 的输入分布重复旧路径。因而当前缺陷不是简单的“状态没传到”，也不是已经排除工程因素后的纯模型能力问题；未通过的候选没有接入生产。

## 全局状态与局部状态

全局状态是唯一权威账本：保存 goal、rolling plan、step revision、action、artifact、audit boundary、机械 evidence gap、协议拒绝和模型/工具身份。Planner 只能声明步骤与成功条件，不能凭声明标记完成；Controller 的机械门先验证 read/write roots，满足后 Auditor 才有语义完成权限。

Selector 局部 State 按 `(step_id, revision)` 持续递归更新，同一步继承前一 Selector checkpoint；换 step、revision、Final 或角色时重置。它只决定一个 operation，不填写参数。

Executor 局部 State 每个已选 action 独立创建，从配置的角色初始 State 开始，接收该 step/dependency 的有界 action facts、当前机械 coverage、唯一被选工具的 schema，然后只填写参数并交给 Harness 执行。执行结果写回全局账本；下一次 Selector 看到更新后的局部因果投影。

Auditor 只在 Controller 的机械前置条件满足后运行；Planner 声称“将读取/验证”永远不能成为完成证据。

## 推理引擎与部署状态

- 2.9B Selector：模型 `rwkv7-g1j-2.9b-vllm-v1`，模型源 SHA-256 `966f3420f833532aae3fb1fd6326533b08d43d23b7b03eaa2f0694a30b64a239`，服务 artifact SHA-256 `c1a316e75abd50f5edc3358fbb2c7d1cb18c611d9b2aa5b888091c8d45cc866c`。
- Head v2 文件 SHA-256 `49538a32162941a256f1075ea465b52bda5ddc07e9e4001f94268f7c4368892a`，逻辑 hash `ef83fd7bf9340977f2ae16d95899690addf3446467ea43a138c61f0926c69bdd`。
- 推理引擎 revision `67f0c5996c50dca0ad779da545cb491527de988f`；真实 canary 和反事实均使用原生 RWKV State transport。
- 13.3B Executor：`rwkv7-g1j-13.3b-zero-state-capability-ctx16384`，模型 SHA-256 `559371f5b9aef13189ae54b345ac096af4ad2b689996c05d89de687612b3ae65`。
- 本机默认 29621 仍指向旧 Head，因此身份检查会按设计 fail closed。由于 Head v2 已被真实 canary 判定不可发布，本轮不把默认服务切换到它。

## 验证与发布判定

- 本次定向状态/Selector 回归：60 passed。
- 完整测试：643 passed。
- 新鲜 wheel 仅包含当前 Selector 的 7 个生产文件，不含已删除的旧 v1 提取/训练入口；wheel SHA-256 为 `45d6ee10be0bed0ce6bbb7d871a0fb6c0257b29c6003baef4522351ea0d48787`。
- 产品判定：**FAIL / blocked，不能发布为可靠 Agent**。
- 工程整改判定：停滞预算、纯读取菜单、ABSTAIN 权限/计数和机械状态投影已修复；Executor 单一输入合同尚未通过真实完整事实链路，因此未替换生产协议。
- 能力整改判定：Selector Head v2 与 13.3B zero-State Executor 仍需在固定代表性评测下重新建立能力；Executor 后续数据必须覆盖长事实、remaining state、命令 operation identity 与严格 JSON。本轮没有 StateTune，也没有为改善结果修改评价口径。
