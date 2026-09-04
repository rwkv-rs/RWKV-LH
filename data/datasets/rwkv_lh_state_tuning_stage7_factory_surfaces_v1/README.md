# Stage7 Factory surface cards v1

- Source: `rwkv_lh_state_tuning_stage7_factory_seed_v1/seed_plan.jsonl`, SHA-256
  `81fbd33f6211dff228a423ab6171255a2b6d2d617ca5f33af5e2757c6c273dbb`.
- Purpose: expand only public request wording and fictional entity/domain surfaces for four
  registered Stage7 defect clusters. These cards do not contain tool, Controller, Gate, state,
  or final-answer labels.
- Version/schema: `rwkv-surface-factory.cards.v1`; 400 train and 100 dev family cards.
- Generation: `RWKV-state-factory` command `rwkv-surface-synthesize`, temperature 0.4,
  single worker, per-seed frozen batch sizes. Accepted batches: Terra 9 and Luna 71.
- Main artifact: `surface_cards.jsonl`, SHA-256
  `9fc77ef19bdd7fd55fb645c32a283838a5f67796111bb57f9272bdb35c0363c2`.
- Raw accepted completions: `batches/*.json`; every digest is registered in `manifest.json`.
- Rejected predecessor: the initial phase seed that added unrequested freshness/comparison
  obligations is isolated under the Stage7 experiment `rejected/` directory and contributes
  zero training rows.
- Validation: schema, placeholder, forbidden-tool-name and exact cross-family duplication gates
  passed. Field-level phrase reuse is reported separately and was not retroactively promoted to
  a hard gate.

The deterministic RWKV-LH generator expands these cards through the current Controller and
ActionHarness into the separately versioned `rwkv_lh_state_tuning_stage7_factory_contrast_v1`
training dataset.
