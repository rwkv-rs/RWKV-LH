# rwkv_lh_g1j_auditor_step_state_tuning_v1

Version: 1

Purpose: Train only the isolated G1J Step-Auditor recurrent State.

Source: `data/experiments/G1J_PER_STAGE_STATE_TUNING_V1_20260902/auditor_step/source_registry.full.jsonl` at SHA-256 `9a1d321bcf46aafc545a3ddb4381b8eef338fdc01bf5c5ff4bdfaf2113ae8fda`.

Generation: the stage-specific frozen generator renders production prompts and targets, uses the registered family split, executes every verifier, and writes canonical UTF-8 JSONL.
