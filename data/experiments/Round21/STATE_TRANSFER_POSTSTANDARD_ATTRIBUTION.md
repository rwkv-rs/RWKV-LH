# Round21 跨任务状态传递：标准答案后归因

## 边界

Post-run join only. Frozen state-transfer chains were generated before standard answer scoring. This report adds external acceptance and failed-check observations after all 90 cases terminated; it never participates in generation, action choice, proof, completion, or final-output delivery.

## 结果

- External：Round20 `17/90` → Round21 `20/90`。
- Round21 新增正确题：E2E-B16, E2E-B17, E2E-B22, E2E-B26, E2E-B28, E2E-M11, E2E-M12；丢失正确题：E2E-B06, E2E-B12, E2E-B29, E2E-H09。
- 盲态发现的状态传递缺口覆盖 14 题，其中 External 错误 `13` 题，正确 `1` 题。
- 可直接确认“先写对、后覆盖错”且中间只传递成功回执：E2E-B02, E2E-B18, E2E-M28。

## 因果解释

Opaque dependency transfer is not sufficient by itself to prove causation, but its scope is material: 13 of 14 affected cases ended externally wrong, and three have a directly observable exact-target write followed by a divergent same-target write. For those three cases the chain is: RWKV produced a correct target; the architecture stored only a success acknowledgement in dependency memory; a dependent RWKV task wrote the same target again without receiving the prior value; the final target diverged. The later wrong value still originates from RWKV; the architecture amplifies it by discarding already-correct observable state.

这不是让控制器保留一个被判定为正确的答案。下一轮只能把每次 RWKV 已执行写入的真实post-action snapshot 作为可审计 observation 传给依赖任务；后续是否读取、如何处理和写什么仍由 RWKV 决定。
