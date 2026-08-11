# RWKV-LH architecture ablation protocol v1

## 目标

定位哪些通用架构层增加了错误、路径重复、请求数或时延，而没有改善外部验收结果。
消融只评估 RWKV-LH 对 G1i-13.3B 的组织方式，不用其他模型替代或掩盖 RWKV。

## 固定环境

- 推理端：vllm-rwkv。
- 模型：`rwkv7-g1i-13.3b-20260805-ctx16384`。
- 执行环境：WSL `UbuntuRecovered`。
- E2E 数据集：`data/datasets/rwkv_lh_e2e_v1/` 中固定的 core30 + lh12，共 42 题。
- 架构回归：同目录中的 LH-Control-30。

## 统一相似度算法

所有轨迹、输出和实验版本比较统一使用 UTF-8 byte 5-gram cosine similarity：

1. 结构化对象先按 JSON key 排序，以紧凑 JSON 编码为 UTF-8；普通输出保留原始文本。
2. 统计连续 5-byte n-gram 的出现次数。
3. 对两个计数向量计算 cosine similarity。
4. 完全相同的空输入相似度为 `1.0`；仅一侧为空为 `0.0`。

固定参数：

- `n = 5`
- 近重复阈值：`0.95`
- exact artifact 通过阈值：`1.0`
- 指标版本：`utf8-byte-ngram-cosine.v1`

协议登记后不得根据实验结果修改算法、参数或阈值。若未来更换指标，必须建立新的协议版本，
并在所有方案上重新计算，不能只重算失败方案。

## 首轮消融因子

按单变量对照运行，随后只对有明确收益的因子进行组合验证：

1. `baseline`：当前完整架构。
2. `no_mandatory_model_cross_check`：保留确定性 verifier，移除每个 required task 后的强制模型复核。
3. `single_action_contract`：将 tool choice、arguments 和 verification design 合并为一次受约束工具动作解析。
4. `no_model_failure_analysis`：由确定性失败类型决定 retry/reselect/replan，不额外调用模型解释同一失败。
5. `task_local_validation_binding`：任务验证只判断当前任务和依赖输出；Goal 完成度只在任务图边界判断。

任何因子必须通过通用接口或配置实现，不得按 case id、文件名或题目文本特判。

## 首轮组合验证登记

Basic-10 单因子试验完成后，`no_mandatory_model_cross_check` 同时改善主结果与请求数，
`no_model_failure_analysis` 降低请求数但主结果弱于前者。按上述协议登记组合方案：

- `minimal_validation_and_recovery`：同时移除 required task 后的强制模型复核，以及确定性失败后的模型失败分析；
  其他数据、参数、阈值、控制流和外部验收保持不变。

组合方案先在相同 Basic-10 上验证交互效应；只有主结果不低于最佳单因子时才可进入完整 42 题。

## 状态语义分离验证登记

`task_local_validation_binding` 的 Basic-10 暴露出独立的运行级状态冲突：规划字段
`goal_criteria` 被提示为“推进”的条件，但完成边界把它解释为“已经满足”的条件。登记后续方案：

- `separated_progress_and_goal_satisfaction`：依赖图单独表达任务推进；`goal_criteria` 只绑定当前任务动作与
  verifier 完成后直接建立的外部 Goal 条件。前置检查、读取和中间观察任务可以为空绑定；完整 Goal 覆盖
  仍只在控制器完成边界检查。继续保留 task-local RWKV 语义校验与模型失败分析。

该方案不得按动作名机械排除只读任务，因为只读结果也可能是用户的最终目标；绑定依据必须是任务是否
直接建立 criterion，而不是动作是否产生副作用。

## 固定评价字段

- Agent completion rate。
- External acceptance rate（主结果）。
- Agent/external false-positive 与 false-negative 数量。
- 每题模型请求数、输出 token、端到端时延。
- retry、reselect、replan 和重复 attempt 数。
- 轨迹相似度及 `>= 0.95` 的近重复路径数量。
- exact artifact similarity。
- 正常、边界、异常输入和历史问题回归结果。

## 晋级条件

消融方案只有在完整 42 题和 LH-Control-30 上都完成后才能下结论。候选整改必须至少满足：

- external acceptance 不低于 baseline；
- false positive 不增加；
- 近重复路径、请求数或时延至少一项有可重复下降；
- exact artifact similarity 对所有通过题均为 `1.0`；
- 全量离线测试及历史回归通过。
