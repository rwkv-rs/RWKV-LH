# Round43 预注册协议：RWKV 已选证据的聚焦 Pass 复核

## 触发证据

Round42将选择与判断完全分离后，selection机械选择第一条旧观察，canary 0/10，已回退。Round41则能选择相关证据，但B04/B27/B29在大catalog中初判pass后没有专注检查所选pair。

## 唯一架构变更

保留Round41 criterion-local请求不变：RWKV在canonical catalog中同时选择refs并初判pass/replan。

若初判为pass且pair通过全部机械contract，再调用同一RWKV做一次focused pass audit：

- 只显示固定criterion、Immutable Goal、RWKV自己选择的binding、初判reason，以及所选actual/expected完整观察；
- 不显示完整catalog、未选候选、Task列表或外部验收；
- 返回恰好`decision=pass|replan`和非空`reason`；
- audit pass才把同一refs和audit reason交给Controller；audit replan返回空binding；
- Controller不比较内容、不改变decision/ref/reason。

初判未提供reason时，audit明确标注为空，不由Controller生成理由。

## 禁止

- 不改变Round41 source role或选择候选；不让Controller预选ref。
- 不做字符串/hash/JSON相等规则，不读取外部验收。
- 不把audit replan改成pass，不编辑RWKV最终答案。
- 不修改格式层、Task规划、Task verifier、action或workspace。

## 固定验证

1. 初判replan不调用audit；初判pass只调用一次audit。
2. audit prompt包含选中pair完整观察和初判reason，不含SOURCE CATALOG或未选ref。
3. audit replan产生空binding、无部分evidence；audit pass refs不变，reason逐字来自audit。
4. pytest、LH-Control 30/30、E2E-90 validate-only 90/90。
5. canary：B04、B27、B29；B05、B06、B08、B11、B12、B13、B18为正确对照。
6. canary后显式B01–B30，对比Round41/Round40。

## 成功判据

- FP不高于1且低于Round41的3；
- Strict不低于17；
- Controller semantic fields generated=false，refs/reason/decision均来自RWKV。
