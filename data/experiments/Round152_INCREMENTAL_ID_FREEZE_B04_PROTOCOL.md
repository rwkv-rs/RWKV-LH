# Round152：Incremental ID Freeze B04 Smoke 预注册

日期：2026-08-23

相对 Round151 只修复 `ContractGraphPatch.create` 对 one-shot existing-ID iterable 的重复消费，并增加
对应单测。Planner wire schema、reasoning_effort=low、任务、模型、verifier、RWKV sampling、full tool
disclosure 和全部 graph budgets 固定不变。

固定 E2E-B04，case concurrency=1，atom concurrency=4。

通过门：

1. correction patch 可引用已有 obligation/node；无 unknown-reference 语义重试。
2. Reviewer 的 source/destination digest gap 由 RWKV correction atom 补齐。
3. external PASS、agent completed、strict PASS。
4. Final byte-exact raw RWKV；GPT tool execution=0；结果胶囊无 process 字段。

通过后才恢复固定 13 题 canary。
