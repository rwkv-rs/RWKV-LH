# RWKV-LH 真实 Agent 能力阶梯 V1 预注册

登记日期：2026-08-30；登记发生在能力阶梯数据生成、当前架构基线运行和后续 old-capability state tuning 之前。

## 目标

建立一个独立于 Full90 的整体 Agent 能力基准。Full90 继续用于环节、边界和历史回归；本基准回答“当前本地项目能连续完成到哪一层真实工作”，不得用单步 Selector/Executor 分数替代。

固定架构：强模型只做 contract-graph Planner/Reviewer；2.9B RWKV Hidden(mean+last)+h64 MLP 只在冻结 25 类名称/描述中选择 operation；13.3B RWKV 生成该 operation 的参数、推进执行并生成 final；Harness 机械校验和执行。Planner/Reviewer 无 Harness authority。

## 五层与固定案例

每层 2 例，共 10 例；全部是端到端闭环，而非单一工具题。

1. `tier1_closed_loop`
   - `AGENT-LADDER-L1-FIX01`：修复一个真实 Python 计价缺陷、补文档并运行公开 verifier。
   - `AGENT-LADDER-L1-DATA01`：读取交易数据、生成严格统计产物和说明并运行 verifier。
2. `tier2_small_workflow`
   - `AGENT-LADDER-L2-CLI01`：创建带 JSON 持久化的小型多文件 CLI，并通过函数与 CLI 测试。
   - `AGENT-LADDER-L2-REPAIR01`：修复跨文件库存事务语义，保持公开 API 并通过回归。
3. `tier3_cross_file`
   - `AGENT-LADDER-L3-WEB01`：在现有原生 Web 应用中完成多文件功能扩展和 Node 行为验证。
   - `AGENT-LADDER-L3-QUEUE01`：修复跨模块队列的持久化、重试与顺序语义并通过回归。
4. `tier4_medium_project`
   - `AGENT-LADDER-L4-LEDGER01`：从零创建用户示例中的简洁个人记账网页，持久化、月统计、删除、公开验证全部通过。
   - `AGENT-LADDER-L4-TRACKER01`：从零创建标准库多模块 issue tracker CLI，含持久化、筛选、统计、导入导出和文档。
5. `tier5_networked_project`
   - `AGENT-LADDER-L5-PACKAGING01`：公开网页取证后创建可验证 Python 项目，并把已提交 evidence URL 写入来源文件。
   - `AGENT-LADDER-L5-RWKV01`：公开检索后创建可搜索的 RWKV 资料网页；本地产物中的引用必须来自已提交 evidence。

具体任务文本、workspace seed 和隐藏 acceptance 由确定性 generator 生成；生成后以 SHA-256 冻结。public verifier 可见且必须保持 byte-exact；隐藏 acceptance、参考结果和 oracle action 不进入 workspace 或模型输入。

## 固定执行配置

- WSL `UbuntuRecovered`、项目根 `/home/chase/GitHub/RWKV-LH`、`uv`。
- 推理实验固定远端物理 GPU0；产品端口 18070 不停止，实验服务使用 18075，本地 Selector 使用 29621。
- Selector 固定 S60/zero；本地 tier1–4 固定 task-level `EXE-G3-MULTISTAGE-STEP2000`；联网 tier5 固定 task-level `EXE-G6-NETWORK-RECOVERY-STEP1500`。
- profile 由 immutable goal retrieval policy 在 run 创建后绑定；一个 atom 的 Executor lane 从建立到结束身份不变，run/atom 内 profile switch=0。
- contract graph、concurrency=3、固定 Planner/Reviewer 配置；每个 case 独立 workspace、state、retrieval snapshot 和 verifier namespace。
- local case retrieval policy=`offline`；network case=`auto_public`。网络工具菜单始终保持冻结 25 类，不因 policy 改变类别或顺序。
- 原始 RWKV text/token/logits/argmax/finish/model/profile/digest 先追加保存；禁止诱导、修改、删除、截断、补全、重排、隐藏或替换。

## 固定评价算法

不使用人工观感或语义相似度。评价固定为：UTF-8 byte-exact SHA-256、JSON/文件集合精确相等、公开 verifier exit code、隐藏标准库 checker、事件/identity 双射。

每例 `strict_pass` 同时要求：

1. RWKV run completed；
2. hidden isolated verifier 全部通过；
3. final 非空，且交付 final 与所选 RWKV raw `final_answer` 的派生 text byte-exact；
4. acceptance 未泄漏，bubblewrap verifier/process tree 完整关闭；
5. Planner action=0、RWKV output rewrite=0、scope violation=0。

联网例另要求：至少一次成功 `web_search` 或指定 connector action；至少固定数量的 content-addressed evidence URL；产物中引用 URL 与已提交 evidence URL 有集合交集，禁止只写伪造引用。

## 固定分层与门槛

- 单层通过：该层 2/2 strict pass。
- 能力 ceiling：从 tier1 起连续 2/2 通过的最高层；低层未通过时，即使高层偶然通过也只报告 isolated pass，不抬高 ceiling。
- 同时报告每层 external pass、completed、strict pass、action/request、协议拒绝和失败簇。
- V1 第一正式简体版候选门槛：tier1–tier4 全部 8/8 strict；tier5 至少 1/2 strict 且 2/2 有真实已提交 network evidence；全项目及历史联网回归无新增失败。
- 当前基线和每个 state 候选均运行完整 10 例；不得只重跑有利案例。transport/provider failure 另分类，但不从分母删除。

## 与 state tuning 的隔离

这 10 个案例是冻结 holdout，禁止进入约 2K state-tuning train/dev。训练数据只从相同能力维度的不同实体、路径、数值和结构族生成；固定 UTF-8 byte 5-gram cosine 检查 train/dev/holdout 泄漏，阈值预注册为 `<0.95`，超阈值行删除后重新冻结，不能改变算法。

先运行当前 S60+G3/G6 基线并按首次偏离聚类，再决定一个通用 old-capability state 是否足够。只有固定消融证明独立功能 state 有净收益且无跨能力回归，才启用多个 state；不按每阶段切换 state。

## 记录要求

生成器、tasks、acceptance、manifest、runner、verifier、状态、引擎、全部 raw/derived 输出和分析均记录 SHA-256。任一失败扩展到同层、同 operation、同 prompt/state 路径；不能用测试特判修复。
