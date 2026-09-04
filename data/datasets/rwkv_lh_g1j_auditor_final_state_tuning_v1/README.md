# rwkv_lh_g1j_auditor_final_state_tuning_v1

Version: 1

Purpose: Train only the isolated G1J Final-Auditor recurrent State.

Source: `data/experiments/G1J_PER_STAGE_STATE_TUNING_V1_20260902/auditor_final/source_registry.full.jsonl` at SHA-256 `509be6fc099da2bb5e247e7df1665374b0c1b4ea6a29c6a316478464d885cabf`.

Generation: the stage-specific frozen generator renders production prompts and targets, uses the registered family split, executes every verifier, and writes canonical UTF-8 JSONL.
