# Live Network Evidence Projection v2 预注册

## 根因基线

真实 `run_r1` 的完整网络访问和 snapshot 均成功，但派生给 RWKV 的 action-result view 过大：

- URL 用例：首轮 1,093 tokens，第一次 evidence 后 3,293，第二次后 5,493，终止轮 9,378；
- GitHub 用例：首轮 1,086 tokens，第一次 evidence 后 3,591，第二次后 9,564；
- 当前 state-tuning 数据的训练上下文为 2,496 tokens；超出后出现重复检索和未写文件却声称已写的原始输出。

完整 `ActionResult`、原始网页、clean snapshot、exact EvidenceRecord 与 RWKV raw journal 已内容寻址或 append-only 持久化。本整改只改变下一轮 prompt 中的派生 evidence projection，不改写任何上述原始记录。

## 固定整改边界

- 最多投影 2 个不同 source；
- 每 source 最多 1 个 span prefix，最多 512 字符；
- prefix 必须逐字等于持久化 source span 的 `[0:n]`，记录 source span ID、prefix SHA-256、原始字符数与投影字符区间；不得把 prefix 冒充为完整原 span；
- 保留 evidence ID、source object ID/type、snapshot digest、URL、title、published、必要 structured fields 与 route/provider identity；
- 完整 evidence 数量与持久化事实必须显式标记；不得删除或修改原始 action result/snapshot/journal。

## 固定指标与门槛

1. unit fixture 的投影 JSON 小于 4,000 字符；
2. source 数不超过 2，span 数不超过 1，span text 不超过 512；
3. prefix exact、prefix SHA-256、source span reference 和 projection range 全部正确；
4. 结构化关键字段仍可见，输入 full result 保持 byte-equivalent canonical JSON；
5. 同一真实 E2E 两个用例的第一次 evidence 后 tool-selection prompt 不超过 2,496 tokens；
6. 2/2 E2E 仍使用同一数据集、模型、采样、provider、retry 与判定门槛；
7. 全量测试通过，RWKV raw journal 的 `postprocessed=false`、raw SHA 和 token IDs 门槛保持不变。

若第 5 项仅因完整工具菜单固定开销无法达到，必须保留实测值并报告，不得调整 2,496 门槛。
