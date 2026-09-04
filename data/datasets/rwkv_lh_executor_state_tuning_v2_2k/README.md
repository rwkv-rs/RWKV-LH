# RWKV-LH Executor State Tuning V2 2K

Role-pure 13.3B Executor initial-state data. Every prompt uses `independent-selector-executor.v1`, contains exactly one already selected tool contract, and contains no Selector menu/output. No model was called.

Train with the target-suffix JSONL only after the remote tokenizer/ctx validation is attached to the manifest. The source test families and Full90 remain excluded.
