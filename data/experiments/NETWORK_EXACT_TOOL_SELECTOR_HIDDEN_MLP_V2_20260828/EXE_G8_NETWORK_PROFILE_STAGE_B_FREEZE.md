# EXE-G8 task-level profile Stage-B execution freeze

Frozen on 2026-08-29 while G8 training was active and before any G8 checkpoint,
holdout, live V1/V2, or retrieval Stage-B model inference.

Stage B may run only when the all-checkpoint G8 offline ablation selects the
earliest checkpoint passing every preregistered G4/G6/G8-holdout gate. It binds
that G8 profile once for the complete Executor task lane and binds S60 zero once
for the Selector lane; within-run state switching is forbidden.

Frozen gates:

1. live V1 strict 2/2;
2. unseen grounded V2 strict 6/6 with every marked field matching committed evidence;
3. S60 literal complete requirement at every Hidden continuation byte tail;
4. Executor literal requirement or rejection-recovery question at every generation tail;
5. zero profile switches per task lane;
6. raw Selector logits and Executor outputs retained and unmodified;
7. retrieval hard gates 9/9;
8. physical GPU0 attested and product port 18070 preserved.

Frozen identities:

- G8 Stage-B wrapper SHA-256:
  `a7ed23c513413ae8fefdc8676012cb2b2be05a1c7887c43f303cddbb77409073`;
- frozen common Stage-B engine SHA-256:
  `9fe17a9d43f946b4f6c462013becfc5f1b12122f1d8336d16c5eb37f743dd3b4`;
- G8 offline ablation runner SHA-256:
  `427dc69c445108eb2ec36eb97e618c74f7259e666519added6a675739ccd6f63`;
- G8 candidate launcher SHA-256:
  `eabc25fe9915465a06f3378ac2c696e2aeae161f469a74f93d61332bc0401fb5`;
- live V2 cases / manifest SHA-256:
  `d8ad5bd999d26b6b16292fae7503534dcb01d3f8ae0c7a1d9c78c93d1d1deb31` /
  `77572aca4d6afcfc0ba4d2c217c93d32f2b2f7476fa506fbbc44060c8dd604f4`;
- live V2 evaluator SHA-256:
  `2dbc1b1a0e978bea8726ad7cd46ced9b25dd05189a774002326a4717d2f8bc25`;
- release/retrieval gate runner SHA-256:
  `3926d1a734103d8d4e6239d77ce4a2a3ac1d2778c6f8b2dad0e7fedf3a3eef96`.

The selected ablation-result and checkpoint-validation SHA-256 values are
required as explicit CLI arguments after natural training completion. A failed
gate remains failed; the runner cannot change sampling, retry, output, or score
rules after observing results.
