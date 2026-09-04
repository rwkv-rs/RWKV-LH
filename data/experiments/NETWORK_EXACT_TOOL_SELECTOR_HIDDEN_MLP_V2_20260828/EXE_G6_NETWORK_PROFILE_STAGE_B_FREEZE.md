# EXE-G6 task-level network profile Stage-B freeze

Frozen on 2026-08-29 (Asia/Shanghai), before G6 checkpoint evaluation,
selection, or any unseen live-network V2 execution.

Stage B may run only if the preregistered all-checkpoint G6 ablation selects the
earliest checkpoint passing every gate. It binds that one G6 state to the
Executor action lane for the complete task, binds S60 zero state to the Selector
lane, and permits no within-run state change.

The fixed Stage-B gates are:

1. frozen live-network V1 passes 2/2;
2. unseen grounded/profile-stable V2 passes 6/6;
3. all marked JSON fields match committed network evidence and the text case
   satisfies its exact-span fragment rule;
4. every S60 decision places the literal complete requirement at the byte tail;
5. every Executor generation places the complete requirement or rejection
   recovery question at the continuation edge;
6. every task has zero per-lane state-profile switches;
7. all raw Selector logits and Executor outputs remain retained and unmodified;
8. the frozen retrieval-quality suite passes 9/9 hard gates;
9. physical GPU0 is attested and the existing product service on port 18070 is
   preserved.

The Stage-B runner SHA-256 is
`9fe17a9d43f946b4f6c462013becfc5f1b12122f1d8336d16c5eb37f743dd3b4`.
The all-checkpoint G6 ablation runner SHA-256 is
`9d6cad204faad0e182e8b307b19070d443275c09bdbe24147c64c2a72a8fb5ad`.
The V2 evaluator freeze SHA-256 is
`ecc94839ce63979b72b8c12380f1ccd7573261cd0d16fbd4457245e445e238b7`.
