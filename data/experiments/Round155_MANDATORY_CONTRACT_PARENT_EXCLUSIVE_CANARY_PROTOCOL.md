# Round155：Mandatory Contract + Parent Exclusive 13-Case Canary 预注册

日期：2026-08-23

## 固定目标与架构

继续验证 `strong-planner-reviewer-rwkv-contract-graph.v1`，不生成训练数据，不启动 Full90。
强模型仍只承担 Planner/Reviewer；RWKV 独占参数生成、工具执行和最终回答。Planner/Reviewer
只收到结构化 result capsules，不接收 RWKV prompt、transcript、arguments、candidate、worker
summary、retry 或 protocol-rejection 过程。

相对 Round154，本轮只固定以下系统性整改：

1. immutable request 产生的所有 obligation 均由本地规则强制 mandatory，Planner 无权降为
   `required=false`；Reviewer 全部判定 satisfied 前 finalizer 不可运行。
2. 文件权限仅由结构化 read/write roots 校验，不再从 objective/check prose 猜测路径；消除
   `before/after`、`TaskQueue.pop` 等误判，同时继续拒绝未授权 scope roots。
3. exclusive atom 单独调度并直接作用于 parent workspace，避免 `run_command` 的文件副作用
   留在一次性副本中而丢失。
4. dependency capsules 后再次附加当前 atom contract，防止小执行器复制上一原子的 operation、
   request id、path 或 value。
5. path mutation 通常保持 action_budget=1；仅显式瞬态恢复任务允许 budget=2，在隔离事务内
   观察失败后重试。
6. Planner 将格式、数据变换和来源关系编译成可观察 predicates；Reviewer 必须逐 token/key/value
   对照真实结果，write-success 本身不算内容证据。

代码基线固定为 `154 passed`。RWKV 与 GPT endpoint 在运行前均通过模型身份检查。

## 固定数据与参数

- 数据集：RWKV-E2E-90 中固定 13 例，顺序为 B04、B09、M10、H09、LH04、LH06、LH08、
  LH09、B22、M15、M16、M24、M28。
- case concurrency=4；RWKV atom concurrency=4；GPT 跨 case 串行。
- GPT-5.4 Planner=medium、Reviewer=medium；transport retry=3；semantic repair=2；
  plan tokens=4000；review tokens=2400。
- max graph patches=8；review rounds=8；graph atoms=48；stagnant rounds=2；
  max transitions=200；full tool disclosure；固定 sampling、verifier 与外部评分。
- 运行目录必须生成 `RUN_PROTOCOL.json`、`source_tree_manifest.json`、逐例 audit/causal ledger、
  `results.json` 和 `REPORT.md`，记录数据来源、版本、摘要与生成参数。

Round154 同一子集基线：TP=3、FP=5、FN=1、OTHER=4；logical GPT=50、physical attempts=54、
GPT total tokens=292463、RWKV actions=82。

## 晋级门

质量门沿用 Round154，不因运行结果修改：

1. strict >=11/13，且 B04、B09、H09 保持 TP。
2. Round154 的 3 个本地异常退出（M15、LH04、M24）不再出现 scope-prose ValueError。
3. Round154 的 5 个 FP 至少 4 个转为 TP；不得新增 external-pass/agent-not-completed FN。
4. 瞬态、恢复、外部副作用用例必须有公开 result-capsule 因果证据，不接受 worker 声称成功。

成本与架构门：

1. logical GPT <=52，中位数 <=4；physical attempts <=65，并单列传输重试。
2. 所有 completed Final 都是 byte-exact raw RWKV；GPT tools=0；controller_rewritten=false。
3. finalizer 只在全部 mandatory obligations satisfied 后执行且 action_count>=1。
4. 至少 5 例存在真实 RWKV atom overlap；GPT 串行不得串行化 RWKV executor。
5. result-only DTO 发现任一 process-field 泄漏则整轮失败。

任一质量门失败则不启动 Full90，使用固定结果继续定位全局根因。
