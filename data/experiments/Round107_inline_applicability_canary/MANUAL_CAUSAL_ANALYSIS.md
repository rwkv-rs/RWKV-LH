# Round107 manual causal analysis

## Fixed result

- Strict/Agent/External: fail/fail/fail.
- 32 model requests, 11 Tasks, 8 Attempts, 0 repairs.
- Final was non-empty raw RWKV output.

## Call-level chain

1. RWKV created eight independent service-read Tasks plus rules, verifier, and report Tasks.
2. Each service Task executed exactly one correct first read.
3. Each lane proposed the next service path. The inline applicability check rejected all
   eight before another Attempt was created.
4. With completion readiness visible in the same rejection event, T2, T4, and T5 selected
   `lh_task_done`. T1 instead repeatedly selected its already-observed subject and entered
   an unchanged loop. T3/T6/T7/T8 remained pending when T1 blocked the run.
5. No migration action ran, so every external acceptance check failed.

## Conclusion

Moving applicability to the Task-step boundary was beneficial but not sufficient: three
lanes committed with no controller completion decision, while one remained stuck. The
cross-file sequence itself shows that RWKV is treating the eight reads as one batch even
though the Goal graph split them into independent lanes. The existing collection/workset
protocol is a better structural match than adding stronger completion rules.
