# G1J Goal Loop v2 真实能力基线预注册

登记时间：2026-09-01T20:25:33+08:00。本文件在本轮端到端模型调用前固定评价口径。

## 问题

回答“当前项目原样可以完成到什么程度”，并把以下四类失败分开：

1. 项目配置/协议集成失败；
2. Strong Planner/Stage Checker 输出失败；
3. RWKV Selector/Executor/Auditor 模型能力失败；
4. GPU、服务、网络或 sandbox 基础设施失败。

不使用任何已训练 State profile，不进行 State Tuning，不在看到结果后修改任务、参数、阈值或评价算法。

## 被测源码与数据

- branch: `chase/rwkv-goal-loop-v2-cleanup`
- commit: `f478b51dc27d2de5f86472c239b431f16e4384c0`
- worktree: dirty；保留用户已有修改，本轮不改产品代码。
- tracked diff SHA-256: `012a38048f4dbe09e9b98263d290b83fdfe5b08a4fa064ba0dc7d95e32454283`
- `rwkv_lh/` Python/Web 源码列表聚合 SHA-256: `0a0475a1a649e6202f429492d763624db24568ecd29e644fbe8cf9befbfcaeb0`
- runner SHA-256: `90f29e10e1965b7e3176222445d1325ab922dda92e65ec5e11010ca7e97de8b9`
- frozen tasks SHA-256: `23cf009831fb38dd05bd3fad69e246a822a59ab6bd725833c6df2aaaf45c93bb`
- frozen acceptance SHA-256: `f95da0b4085cdee3bc4555255dfb4f09d9272c00982634c72a040361c5774e06`
- 数据来源/版本：仓库内置 `rwkv_agent_capability_ladder_v1`；用途为不进入 State Tuning 的真实 Agent holdout。生成方式和 hidden acceptance 由该数据集 manifest/runner 固定。

## 固定案例

每层选一个预先固定的代表任务，全部执行，不因低层失败删除高层案例：

1. `AGENT-LADDER-L1-FIX01`
2. `AGENT-LADDER-L2-CLI01`
3. `AGENT-LADDER-L3-WEB01`
4. `AGENT-LADDER-L4-LEDGER01`
5. `AGENT-LADDER-L5-RWKV01`

## 固定架构与模型

- Strong model: Planner，并在每个 stage 结束后作 Stage Checker；当前环境为 `gpt-5.4-mini`。
- RWKV 2.9B G1J: 唯一 25 类 operation Selector；必须记录 model/head/input-protocol 完整 identity。
- RWKV 13.3B G1J: 生成已选 operation 的参数、执行结果汇报与 Auditor；Executor/Auditor 使用独立会话和干净初始 State。
- GPU 仅允许远端物理 GPU0/GPU3。
- G1J 权重：`rwkv7-g1j-2.9b-20260831-ctx16384.pth` 和 `rwkv7-g1j-13.3b-20260831-ctx16384.pth`。
- 不使用 G1I G3/G6 或任何其他已训 State。

## 两个严格分离的运行

### A. Current-product gate

按当前 `.env`/`.env.local` 和当前产品协议运行只读 preflight。若 identity、端口或协议不匹配，立即 fail closed；这是当前产品能力结论，不记为模型质量失败。

### B. G1J zero-State compatibility diagnostic

仅当 current-product gate 因已知 v8 Selector artifact/head 缺失而失败时，允许用已内容定址的 G1J S60/v7 zero-State Head 执行上述五个案例，用于定位除 v8 Selector 以外的编排和 Executor 上限。该运行必须标记为 compatibility diagnostic，不得宣称为最新 v8 产品通过。

## 固定参数与阈值

- supervisor=`openai`，strategy=`contract_graph`，stateful-goal=`true`，independent-selector=`true`
- tool disclosure=`progressive`，concurrency=`1`，max transitions/case=`120`
- 每例 strict pass 必须同时：agent completed、external acceptance pass、strict acceptance pass、final 非空、无 acceptance 泄漏、无 Planner 直接执行工具。
- 能力 ceiling：从 L1 开始连续 strict pass 的最高层；低层失败后的高层通过只记 isolated pass。
- 记录首个可证实失败事件、完整 raw trace 定位、Planner patch/Stage Checker/Selector/Executor/Auditor 输入输出、协议拒绝、tool 执行和 verifier 结果。
- 评价是确定性 verifier/JSON/identity 精确匹配，不使用主观评分或临时相似度口径。

## 停止规则

基础设施不可达、Strong Planner 不可达、完整 Selector identity 不存在，或任一服务超过固定 timeout 时 fail closed。不回退到 Executor 选工具，不用规则/强模型替代 2.9B Selector，不修改用例或隐藏失败。
