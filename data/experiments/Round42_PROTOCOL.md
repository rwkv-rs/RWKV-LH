# Round42 预注册协议：RWKV 证据选择与聚焦比较分离

## 触发证据

Round41的B04、B27、B29已经选择合法独立证据，但在包含完整catalog的同一请求中仍把明显不等判断为pass。B29已选择backup完整snapshot与source原始read，排除格式、缺证据和自引用候选根因。

## 唯一架构变更

每个criterion-local Goal请求拆为两个均由RWKV完成的阶段：

1. **Selection**：只从Round41 canonical catalog返回`decision=select|replan`和一个无reason的binding。model boundary验证ref与eligible pair；非法时仍在selection阶段重试一次。
2. **Focused comparison**：只展示固定criterion、Immutable Goal摘要、选中的actual完整观察和expected完整观察；不再展示其它候选、Task列表或完整catalog。RWKV返回恰好`decision=pass|replan`和非空`reason`。
3. comparison=pass才把相同refs和RWKV comparison reason返回Controller；replan则binding为空。Controller依旧对全部criterion原子聚合并运行原provenance validator。

完整观察来自现有MemoryEntry/Immutable Goal；不计算新值、不使用外部验收。内容超过已有单观察上限时保留明确truncated标记并要求证据不足时replan。

## 禁止

- Controller不比较字符串、hash、JSON或测试结果，不生成decision/reason。
- 不根据criterion关键词选择refs，不把非法pair自动改为合法pair。
- 不把comparison replan改成pass，也不修改最终回答。
- 不更改格式转换层、Task规划、Task verifier、action或workspace。

## 固定验证

1. selection和comparison为两个独立审计请求；comparison prompt不含未选source ref或完整catalog。
2. 非法selection只重试selection，不进入comparison；拒绝JSON不回显。
3. comparison replan产生空binding且无部分evidence。
4. comparison pass保留原refs，reason逐字来自RWKV。
5. pytest、LH-Control 30/30、E2E-90 validate-only 90/90。
6. canary：B04、B27、B29（FP），B05、B06、B08、B11、B12、B13、B18（Round41恢复对照）。
7. 显式B01–B30，对比Round41/Round40。

## 成功判据

- FP低于Round41的3且不高于Round40的1；
- Strict不低于Round41的17；
- 所有比较结论仍来自RWKV，Controller semantic fields generated=false。
