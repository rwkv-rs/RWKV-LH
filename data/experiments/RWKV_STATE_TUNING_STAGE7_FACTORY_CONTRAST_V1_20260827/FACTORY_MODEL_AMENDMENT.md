# Factory 生成模型修订（训练前）

日期：2026-08-27；状态：surface 生成中、Harness 数据未生成、训练未开始。

固定 API 网关上的 `gpt-5.6-terra` 已完成 9 个合格 batch（phase 全 125 family、role train
前 20 family），之后同一 role schema 连续出现原始 HTTP 500
`new_api_error/do_request_failed`。缩小 batch、唯一 schema name 和单并发均验证后，1 条
`gpt-5.6-luna` 的相同 role smoke 在 15.3 秒内通过严格 schema 和 Harness 回放。

因此从未完成 batch 起固定切换为 `gpt-5.6-luna`，不重写已通过的 Terra 输出。原因与约束：

- 两个模型都只能生成公开 surface，不拥有 operation、参数、状态或答案标签；
- 每个 batch 必须记录实际 model，最终 manifest 报告逐模型 batch 数，禁止用单一 model 字段掩盖；
- train/dev 均继续按预登记 family 切分，所有 card 仍经过同一 placeholder、禁词、去重、污染和
  Harness/Controller 门禁；
- 已完成 Terra batch 的 ID 固定，不根据内容分数挑选；未完成 batch 全部使用 Luna，不做逐条
  model 选择；
- 该修订只恢复数据表面扩展，不改变 2,000/400 配额、训练参数、parent 或验收阈值。
