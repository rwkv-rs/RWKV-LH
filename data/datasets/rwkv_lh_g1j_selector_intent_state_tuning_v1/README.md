# rwkv_lh_g1j_selector_intent_state_tuning_v1

Version: 1

Purpose: Train only the isolated G1J Selector-Intent recurrent State.

Source: `data/experiments/G1J_PER_STAGE_STATE_TUNING_V1_20260902/selector_intent/source_registry.full.jsonl` at SHA-256 `8bb946e3bb831aa75c23944c3f02c10c9ff7233b2b738b7f1671ee301859290d`.

Generation: the stage-specific frozen generator renders production prompts and targets, uses the registered family split, executes every verifier, and writes canonical UTF-8 JSONL.
