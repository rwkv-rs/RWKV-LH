# Stage5 结果：停止门通过，但过早完成破坏局部依赖

日期：2026-08-27

## 有效性

- parent 仍为 Stage1 step500；final step1220 SHA
  `6b692dc631f22dc1109138addc36d877308040f688420ea29e7b28d577dc2085`；
- 61 个 tensor 全 finite/nonzero，parent-child cosine `0.9823194681`；
- loss 1220/1220 全 finite，last-64 mean `0.0077963695`；
- tokenizer/BOS/target-suffix、vLLM direct `[V,K]` attestation 通过；
- 工程回归 319 passed。

## 冻结行为

Round1 dev200 operation 199/200；唯一回归为 privacy gate，期望 `web_search` 以触发 Gate，实际
过早 `final_answer`。Stage5 own dev240 为 220/240；mixed local-first 22/32，completion
62/64。

ECRA route120 B：

- first-tool exact 77/120；
- local-only 23/30、public-web 21/25、deterministic 15/15；
- connector 12/20、mixed local-first 3/20、privacy local-first 3/10；
- network macro-F1 `0.9488491049`，local network FP 0；
- required-online FNR `0.1384615`，超过 0.10；
- failed/interrupted 1/120，首次通过 `<=4` 停止门。

## 判定与 Stage6 输入

Stage5 未通过 safety gate，不作为 Stage6 parent。240 条 completion selector 成功把 interrupted
从 9 降到 1，但权重过大：模型在尚未读取本地依赖时选择下游工具或直接结束。Stage6 从 Stage1
开始，完整恢复 Stage4 的 640 条新边界锚，只保留 80 条 completion；另保留 Stage5 的 40 条
focused connector，并新增 40 条普通网页 hard negative。目标是在 Stage4 的 mixed/privacy
基础上获得 Stage5 的停止改善，而不是沿失败 checkpoint 继续修补。
