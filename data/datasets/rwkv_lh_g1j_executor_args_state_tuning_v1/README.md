# rwkv_lh_g1j_executor_args_state_tuning_v1

Version: 1

Purpose: Train only the isolated G1J Executor-Args recurrent State.

Source: `data/experiments/G1J_PER_STAGE_STATE_TUNING_V1_20260902/executor_args/source_registry.full.jsonl` at SHA-256 `bf2d1ba28ea1f3e234cdb585c10c75d3e84d6a2d9b4dd15f0cbc7f1da17a005d`.

Generation: the stage-specific frozen generator renders production prompts and targets, uses the registered family split, executes every verifier, and writes canonical UTF-8 JSONL.
