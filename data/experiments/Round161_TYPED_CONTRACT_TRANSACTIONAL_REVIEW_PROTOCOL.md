# Round161：Typed Contract + Transactional RWKV Executor 分阶段验证协议

日期：2026-08-23

## 目的与冻结基线

本轮验证 Strong Planner/Reviewer + RWKV Contract Graph 的五项系统性改造。主 Supervisor
固定使用 `gpt-5.6-terra`；RWKV g1i-13.3 仍是唯一工具操作者、参数生成者和 Final 主体。
不生成训练数据，不用 hidden verifier 反向修改规则，不为单一用例加入特判。

固定对照：

- R126 canonical Full90：TP/FP/FN/OTHER=`36/30/0/24`。
- Round148 Full90：`41/16/2/31`，logical GPT=`521`，GPT total tokens=`3,309,000`，
  RWKV actions=`624`。
- Round158 Contract Graph Full90：`34/9/4/43`，logical/physical/returned GPT=
  `344/451/319`，GPT total tokens=`4,506,270`，RWKV actions=`560`；26 例 plan unavailable，
  45 interrupted，2 running。
- Round160 terra FP trap：M04/M08=`0 TP / 0 FP / 2 OTHER`；它证明 terra 本身不能替代
  本地契约和执行架构。

## 冻结的五项改造

1. **Typed Contract IR**：Planner 必须把路径、来源引用、JSON pointer/key、精确文本/模板、
   排序、聚合/摘要、换行与保留关系编译为类型化 assertion；自然语言 predicate 只作说明。
2. **Deterministic Checker + Exception-only Reviewer**：可由公开 result capsules 完整判定的
   assertion 在本地完成审核；只有 unsupported、unresolved 或相互冲突的 assertion 才请求
   GPT Reviewer。checker 不读取 hidden verifier。
3. **Narrow RWKV Transaction**：单个 RWKV atom 允许 2--4 个同 scope 操作组成
   read/inspect -> mutate/transform -> verify 的窄事务；RWKV 仍独占所有真实工具调用。
4. **Latest-state Capsule + Correction Signature**：Supervisor 只接收每个对象最新、因果完整的
   result-only capsule；不发送 RWKV 过程。相同失败状态不得重复请求同一 correction，必须换
   策略或安全终止，并持久化签名。
5. **Reliable Routing + Unified Terminal/Scope**：terra 为 primary，配置化 fallback/circuit
   breaker 与 validated plan cache；任意异常必须形成 terminal event；用户授权目录的后代和
   已验证 discovery 路径可进入后续节点，mutation 仍须在提交前通过 DAG 与 scope 校验。

除上述五项及其必要测试/文档外，不改变工具实现、任务、external verifier、分类口径或
相似度算法。

## 数据来源、版本与生成方式

- Suite：`data/datasets/rwkv_e2e_90_v1/`，版本 `v1`。本轮从同一固定 90 例中抽取两个
  预注册子集；只有两个门均通过才运行 `--suite all`。
- 生成方式：`scripts/run_rwkv_e2e_benchmark.py` 创建隔离 workspace、调用真实 RWKV/terra、
  执行 external verifier，并写出 `RUN_PROTOCOL.json`、`source_tree_manifest.json`、逐例
  `audit.json`、`results.json` 与文件 SHA-256。
- 用途：架构消融、回归与成本比较；结果不能直接视为 state-tuning 正样本。错误 acceptance
  仅可作为负例/纠错种子。

## 固定运行参数

- Supervisor primary=`gpt-5.6-terra`；reasoning=`medium`；plan/review token 上限=
  `4000/2400`；transport retry=`3`；semantic repair=`2`。
- max graph patches/reviews/atoms/stagnation=`8/8/48/2`；case max transitions=`200`；
  atom concurrency=`4`；case concurrency=`4`；GPT 请求保持全局串行。
- tool disclosure=`full`；其余 RWKV sampling、工具与 external verifier 沿用 Round158。
- GPT tool execution count 必须为 0；completed Final 必须与 raw RWKV Final byte-exact。

## Stage A：15-case defect canary

固定顺序：B10、B13、B21、B22、B24、B25、M04、M05、M08、M15、M23、M24、M27、
M29、LH06。

质量门：

1. strict TP `>=12/15`、FP=`0`、FN `<=1`、running=`0`。
2. `contract_plan_unavailable=0`；所有异常均有唯一 terminal event。
3. M04/M08 不得再次错误 acceptance；M15/M23 不得因合法后代 scope 抛出未捕获异常。
4. 0 个相同 correction signature 被重复提交；所有 typed-local acceptance 都包含逐 assertion
   evidence/ref/result。
5. logical GPT `<=60`、中位数 `<=4/case`；只统计真实调用，cache hit 单列。

Stage A 任一门失败，停止，不运行 fixed13 或 Full90。

## Stage B：Round155 fixed13 回归

固定顺序：B04、B09、M10、H09、LH04、LH06、LH08、LH09、B22、M15、M16、M24、M28。

沿用 Round155 预注册门：strict `>=11/13`，B04/B09/H09 均为 TP；历史本地异常消失；
FP 恢复至少 4 例；FN 不增加；logical GPT `<=52`、中位数 `<=4`、physical `<=65`；
至少 5 例存在真实 RWKV atom overlap。

Stage B 任一门失败，不运行 Full90。

## Stage C：Full90 晋级门

仅 A、B 全部通过后启动。Full90 固定门：

1. 90/90 持久化、running=0、runner/verifier infrastructure failure=0。
2. strict TP `>41`、FP `<=9`、FN `<=1`；B/M/H/LH 至少 `24/11/3/1`。
3. logical GPT `<344`、GPT total tokens `<4,506,270`；同时报告 cache hits、local reviews、
   exception-only GPT reviews、physical attempts、RWKV actions/rejections/overlap。
4. obligations 与 typed assertions 在 revision 0 后冻结；无 process-field 泄漏；GPT tools=0；
   raw Final 一致；所有 terminal、fallback、cache、correction signature 可审计。

任一结果失败都如实保留，不事后修改阈值或评价口径；后续整改另开新 Round。
