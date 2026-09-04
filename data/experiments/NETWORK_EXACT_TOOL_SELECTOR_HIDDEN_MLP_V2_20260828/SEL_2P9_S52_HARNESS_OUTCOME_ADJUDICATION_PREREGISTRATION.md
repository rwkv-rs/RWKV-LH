# S52 request-last Harness 结果裁决预注册

日期：2026-08-29（Asia/Shanghai）

## 前置事实

成对 dev 实验已经结束，且严格按照原预注册判定为两臂均失败：S51/V3 h64 与 S52/V4 h64 的 natural dev accuracy 都是 `0.9824561476707458`，但 `run_command` 的 6 个样本中各错 1 个，未达到逐类 recall 0.90。不得回写或降低原门槛。

错误审计同时证明 R132 `external_passed` 路径不是唯一 canonical 路径。例如要求创建 JSON 的已通过旧轨迹可以使用 `write_file`，而 `write_json` 也能合法完成；因此“逐字模仿旧路径”只作为诊断指标，不能替代真实 Harness 结果。到本文件登记时，S28/S39/S51/S52 的 test label 均尚未在本轮打开。

## 冻结候选

- 对照 A：S51/V3 h64。
  - Head 文件 SHA-256：`677f55ba762d0cfc3823163b7393cb8744683390a830eb8ce86b220d55a0b0d2`
  - Head hash：`27624ee2c7894ae2821fda0eb3283a9a9604537d20c0ad9eeecb2af31591c8a0`
  - Model hash：`40f9ea8a457fcb6944ca890c4788d402c88a2eba836f697542e679a386d3e10f`
- 候选 B：S52/V4-request-last h64。
  - Head 文件 SHA-256：`a1015319ade76d757013c9db41438f2cc7d1cdd7d13f4bac683896f4428d445c`
  - Head hash：`84f89789d8d31c54ce03551fa217cd38ab37d32c7b8d2f5d0fcf1136024c4b1a`
  - Model hash：`ab08dcbd9d6b37518747a05750e9b694522eccfe61f5f3760c6816c5e3547a4b`

固定选择 h64 的原因是它是预注册容量顺序中的最小候选，并在两臂均有更好的 S39 retention；不再训练、不换容量、不调温度、不改 Head。

## 锁定离线诊断

canonical operation exact equality 仍为固定的 0/1 相似度算法，同时报告 accuracy、macro-F1、逐类 recall 和 confusion；不得改变口径。

- S28 test：accuracy 与 macro-F1 均不低于 0.99。
- S39 test：accuracy 与 macro-F1 均不低于 0.96。
- natural test 中 `synthetic_natural_disjoint` 子集：accuracy 与 macro-F1 均不低于 0.96，所有有支持类别 recall 不低于 0.90。
- natural test 中 `r132_external_passed_original_route` 子集和固定 canary6 的 route-prefix exact 只报告，不作为真实成功 gate。
- A/B 使用各自配对 feature，原始 logits 全量保存；只使用原始 argmax，不做后处理。

## 真实 Harness 主 gate

- 架构固定为独立 2.9B Selector + 独立 13.3B Executor EXE-G2-V3-RL step1250；两个 state 分开持久化。
- Selector 只看 25 个名称/描述、任务、进度和当前阶段问题；Executor 才看所选工具 schema，并把 `current_requirement` 放在续写点前的最后字段。
- 固定 canary6：6/6 strict pass。
- 固定 live-network2：2/2 strict pass，且第一网络操作正确、证据被落盘并核验。
- 固定 Full90 必须完成 90/90 调度并报告所有失败；不加入 benchmark-only `mock_api`，不做案例特判。
- 固定 9 例 retrieval quality gate 必须全部继续通过；路由成功不能代替来源质量。

只有 B 通过锁定唯一标签门槛、canary6、live2 和检索质量门槛，且相对 A 没有新的系统性回归时，才允许作为本地联网第一版。Full90 若未达到真实 Harness 目标，必须明确把剩余问题留给下一阶段 state tuning，不得宣称整个中期目标已完成。

## 原始输出与状态边界

所有 Selector logits、13.3B 原始生成、工具原始结果 envelope、state 引用和哈希均保存。禁止诱导、修改、删除、重排或隐藏 RWKV 原始输出。V3 与 V4 state 目录分开；零 state 与 tuned state 目录分开；任何身份不一致均 fail closed。
