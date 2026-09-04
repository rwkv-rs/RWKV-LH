# Strong Planner Semantic Schema Remediation V1

## 结论

可以采用这一修改。V3 的强模型输出格式不是瓶颈：82/82 次正式调用都返回可解析单 JSON；6 次本地拒绝全部属于跨字段或图因果语义。contract-plan v8 把 `kind/effect_ceiling` 的合法组合放进嵌套 `anyOf`，并在 `depends_on` 字段说明已有目标的最新读取依赖。它不增加格式训话，不选择工具，不生成参数，也不修改供应商原始输出。

固定 5 题真实 API canary 在 `semantic_repair_attempts=0` 下全部首轮通过：

- HTTP 200、单 JSON、strict Schema：5/5。
- 合法 kind/effect 配对：5/5 case、全部 emitted atoms。
- 本地完整语义编译：5/5；semantic rejection 0。
- 已有目标读取依赖：2/2；其中最新读取题直接依赖 `NODE-read-readme-latest`。
- `request` 位于 user payload 最后字段：5/5。
- 原始 assistant content 逐字节保存并复核：5/5；未提取、修复、重排、截断或替换。
- 产品本地健康检查：运行前 200，运行后 200；未调用 RWKV，未使用 GPU。

## API 输入—输出规律

冻结 V3 正式轨迹的 82 次调用显示：平均输入 14,762 字符、输出 2,243 字符、延迟 18.5 秒；输入长度与延迟 Pearson 约 -0.037，说明延迟并不由输入长度单独解释。contract-plan 内输入与输出长度负相关，主要因为小输入生成完整初始图，而长输入多为返回小型修复 patch。格式、解析和 transport 均稳定，剩余问题应当在 Schema/图约束处处理，而不是继续给强模型堆格式提示。

本 canary 平均输入 1,606 字符、输出 1,187 字符、延迟 6.1 秒。它只证明精简固定输入上的 v8 可行，不把 5 题延迟外推为正式服务吞吐。

## 修改边界

- contract-plan response schema 编号由 v7 升为 v8。
- work atom 使用三个互斥分支：investigate、mutate、verify，各自只暴露对应 effect ceiling。
- finalizer 固定 `synthesize + local_read_only`。
- 不使用 Structured Outputs 不支持的 `allOf` 或 `if/then/else`；根对象保持 object。
- 本地语义验证继续 fail-closed；没有把非法输出机械改成合法输出。
- Selector 仍负责具体工具选择，13.3B Executor 仍负责参数和执行；强 Planner 没有获得这两项权限。

## 回归

- 定向：35 passed。
- 全量：654 passed，0 failed，1 个既有 multiprocessing fork deprecation warning。

## 限制与下一步

5 题 canary 不是完整真实 Agent 发布分数。下一步仍需在冻结真实能力集上验证完整 Planner→2.9B Selector→13.3B Executor 链，并继续处理 V3 暴露的 Executor schema generation 失败；之后才进入约 2K 的 Selector/Executor state-tuning 消融。

官方 Structured Outputs 约束参考：`https://developers.openai.com/api/docs/guides/structured-outputs`。
