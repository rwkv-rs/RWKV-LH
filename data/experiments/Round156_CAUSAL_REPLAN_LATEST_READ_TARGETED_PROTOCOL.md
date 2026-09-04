# Round156：Causal Replan + Latest Read 5-Case 定向预注册

日期：2026-08-23

## 固定目的

本轮只验证 Round155 已由固定 13 例定位出的四个系统根因，不改变外部评分，不生成训练数据，
不直接启动 Full90。代码基线为 `156 passed`。

固定用例与对应验证面：

- E2E-M10：修正图必须产生公开 `replan_applied`，文件 exact 与 transient recovery 同时通过。
- E2E-M15：`docs/` 下的 relative path 必须去掉 `docs/` 前缀。
- E2E-M24：每次改写现有 `queueing.py` 必须直接依赖最新成功内容读取，禁止 blind writer。
- E2E-LH06：验证 medium Planner 遇到 5xx 后在同一逻辑调用中降级 low 的传输恢复。
- E2E-LH04：Planner 必须显式编译 JSON container keys；Reviewer 以 immutable request 为准。

## 固定架构与参数

- `strong-planner-reviewer-rwkv-contract-graph.v1`；GPT-5.4 Planner=medium（5xx fallback=low）、
  Reviewer=medium；RWKV g1i-13.3 生成参数、调用工具和输出 raw Final。
- result-capsule-only 边界不变；不向 GPT 发送 RWKV arguments、prompt、transcript、candidate、
  worker summary、retry/rejection 过程。
- case concurrency=4；atom concurrency=4；GPT 串行；transport retry=3；semantic repair=2。
- plan/review tokens=4000/2400；graph patches/reviews/atoms/stagnation=8/8/48/2；
  max transitions=200；full tool disclosure；固定 sampling 与 verifier。

数据来自固定 RWKV-E2E-90 catalog；runner 继续生成 source tree manifest、输入摘要、逐例 audit、
causal ledger、结果和报告。

## 固定通过门

1. strict >=4/5，且 M10、M15 必须 TP。
2. M10 的 `replan_applied` >=1；M15 输出 path 为 `a.txt`、`nested/b.txt`、
   `nested/deep/c.md`。
3. M24 不得出现无最新 read dependency 的 correction writer；若 external=false，必须由公开测试结果
   阻止完成，不得 FP。
4. 无 `contract_plan_unavailable`；如发生 medium 5xx，必须记录 fallback 且后续 low attempt 返回。
5. logical GPT <=22，中位数 <=4；所有 completed Final 为 raw RWKV；无 result-only 泄漏。

通过后仍需回到固定 13 例复验，不能由本轮小子集直接晋级 Full90。
