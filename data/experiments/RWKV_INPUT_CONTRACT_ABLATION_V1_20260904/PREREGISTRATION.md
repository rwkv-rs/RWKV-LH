# RWKV 输入合同零 State 消融预注册

日期：2026-09-04（Asia/Shanghai）

## 目标

在不训练、不加载任何 StateTune 的前提下，区分当前失败来自输入合同还是具体 RWKV 角色能力。先验证输入布局，胜出后才替换唯一生产协议；不得在生产目录并存多代候选协议。

## 固定身份

- Selector 基础模型：`rwkv7-g1j-2.9b-vllm-v1`，服务权重 SHA-256 `c1a316e75abd50f5edc3358fbb2c7d1cb18c611d9b2aa5b888091c8d45cc866c`。
- Selector Head v2 基线 SHA-256：`49538a32162941a256f1075ea465b52bda5ddc07e9e4001f94268f7c4368892a`；该 Head 只能评价原协议，不得用于判定新协议能力。
- Executor：`rwkv7-g1j-13.3b-zero-state-capability-ctx16384`，SHA-256 `559371f5b9aef13189ae54b345ac096af4ad2b689996c05d89de687612b3ae65`。
- Selector 与 Executor State profile 均固定为 `zero`；本实验禁止 StateTune。
- 推理引擎 revision：`67f0c5996c50dca0ad779da545cb491527de988f`；使用原生 RWKV State transport。

## 冻结问题入口

- 固定真实用例：`AGENT-LADDER-L1-FIX01`。
- Selector 基线输入 1,455 tokens，完整 25 工具描述后又在嵌套字符串中重复 eligible 工具描述；内层 `eligible_tools` 不含 `ABSTAIN`，外层 `eligible_labels` 包含 `ABSTAIN`。Head v2 选择 `ABSTAIN`，置信度 `0.8518835041612606`，`read_file` logit `0.4133441150188446`。
- Executor 基线第二轮可见输入约 1,418 tokens；`missing_read_roots=[verify_project.py]` 位于约 token 1,057，之后又出现把 `pricing.py` 放在前面的完整原始 requirement、工具 schema 和通用问题。输出仍为 `read_file(path=pricing.py)`。

## Selector 固定候选

只比较两个输入合同：

1. `S0`：当前生产字节布局，不修改。
2. `S1`：一个菜单权威、一个 frontier 权威的紧凑布局。bootstrap 只出现一次固定 25 类菜单；每轮 delta 不重复描述，不嵌套转义 JSON，字段顺序固定为 role、scope、progress、completed effects、remaining effects、eligible labels、abstain condition、current question。`ABSTAIN` 在所有权限字段中一致；current question 位于末尾，并明确只选择 operation class、不选择 path 或参数。

S1 必须重新以匹配 renderer 的 zero-State 2.9B hidden features 训练一个全新 Head；禁止用 v2 Head 评价 S1。Head 结构、优化参数、固定 seed 和 train/dev/sealed 隔离沿用已冻结 v2 方案，只改变预注册的输入布局与覆盖维度。训练数据必须覆盖中文/英文、单/多 root、完成前后、不同 eligible 集合和所有 25 类；Capability Ladder 十个用例保持 holdout，不进入训练或选择 checkpoint。

Selector 门槛：固定 public dev accuracy/macro-F1 均不低于 0.90、每类 recall 不低于 0.75；完整十例 Ladder 的每个机械上可判定 frontier 均不得选择不匹配 operation 或错误 `ABSTAIN`。若失败，不修改阈值或在运行时加规则替 Selector 选工具。

## Executor 固定候选

只比较两个第二轮 `read_file` 输入：

1. `E0`：当前生产布局。
2. `E1`：同一工具合同和同一全局事实，但最终生成 payload 直接携带结构化 `execution_state`，包括 completed action arguments、remaining read/write roots、completion precondition 和 constraints。原始 requirement 不在机械 remaining state 之后再次重复；尾部问题明确要求从 remaining roots 填写一个参数，并禁止重复 completed arguments。

E1 不替 Executor 选择 path；remaining roots 是 Controller 根据 Planner roots 与成功 Harness action 已机械确定的权威事实。不得添加模型调用、规则补写参数或输出修复。

Executor 首个固定门槛：同一原生 zero-State 13.3B、同一 `read_file` 选择、同一工作区下，第二轮必须生成合法参数且 `path=verify_project.py`，0 次协议拒绝。随后运行完整十例 Capability Ladder；评价口径保持原 verifier。

## 顺序与停止条件

1. 先保存 S0/E0 的逐字段顺序、token 位置和 hash。
2. 实验候选仅放 `temp/` 与本实验目录，不进入生产运行目录。
3. 先运行 E1 单点和同类多-root/read-only 场景；通过后才替换唯一 Executor 协议并全量回归。
4. 再生成 S1 固定数据、抽取特征、训练唯一候选 Head，并先跑 public dev、再开 sealed/Ladder。
5. 任一候选失败则如实记录；不得增加候选、调阈值或执行 StateTune。
