# RWKV-LH State Tuning Stage 8 mutation-stop seed

Dataset version: `rwkv-lh.state-tuning.stage8-mutation-stop-seed.v1`

## Motivation

The post-prompt-remediation E2E-B02 trace completed correctly but exposed two
selector defects in the deployed Stage7 state:

1. an investigate atom read its declared source successfully and then tried to
   read a downstream output that did not exist;
2. a mutation atom repeated the same successful `write_json` three times, with
   the second and third calls producing no workspace change.

Stage7's `no_progress_success_stop` cluster covers successful local reads and
unavailable public providers. It does not cover successful workspace mutations,
identical idempotent mutation results, narrow investigate-atom completion, or
verify-atom evidence completion. Stage8 adds those missing state surfaces.

## Frozen composition

- Factory-generated semantic surface families: 400 train and 100 dev.
- Each family renders four contrastive selector states.
- New selector rows: 1,600 train and 400 dev.
- Stage7 safety/routing anchors: 400 train rows, selected deterministically
  before Stage8 generation.
- Final count: 2,000 train and 400 dev.
- Train/dev semantic families must be disjoint.
- The frozen contamination metric remains `utf8-byte-ngram-cosine.v1`; maximum
  similarity to registered holdouts must remain strictly below 0.75.

## Cluster contract

| Cluster | Required selector contrast |
| --- | --- |
| `mutation_success_stop` | mutation required → mutation operation; exact mutation committed → `final_answer`; identical no-change replay → `final_answer`; changed required value → mutation operation |
| `investigate_scope_stop` | source unobserved → source read; source complete → `final_answer`; downstream target missing after source observation → `final_answer`; source incomplete → continued source read |
| `verify_evidence_stop` | source evidence missing → source read; source present/target missing → target read; both exact observations present → `final_answer`; target observation incomplete → continued target read |
| `idempotent_repeat_stop` | target wrong → mutation operation; first successful exact mutation → `final_answer`; identical_result_count=2 with unchanged digest → `final_answer`; unrelated success with target still wrong → mutation operation |

The factory may produce only fictional entities, domains, and natural request
templates. It cannot produce operation names, parameters, state labels, expected
answers, Controller events, or verifier decisions.

## Source and generation

- Root-cause source:
  `data/experiments/LOCAL_NATIVE_ENGINEERING_REMEDIATION_V1_20260827/strong_planner_canary_post_auth/run_e2e_b02_prompt_grounding_v2/cases/E2E-B02/audit.json`
- Source SHA-256:
  `225866022637f78f495bccad81892bb9001edac551f81a22ccc1bd168352e0f8`
- Surface generation: `rwkv-surface-synthesize` from the independent
  `/home/chase/GitHub/RWKV-state-factory` repository.
- Action generation, execution, rendering, validation, contamination checks,
  and final export remain owned by RWKV-LH.

