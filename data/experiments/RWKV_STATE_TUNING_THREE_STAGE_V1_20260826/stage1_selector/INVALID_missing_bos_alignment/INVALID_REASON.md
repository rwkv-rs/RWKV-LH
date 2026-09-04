# INVALID: training/inference BOS mismatch

The run was manually stopped after 78 recorded optimizer steps. vLLM prepends RWKV BOS token 0 because
the production completion request uses `add_special_tokens=true`; the original RWKV-PEFT JSONL path did
not prepend that token. Its teacher-forcing trajectory therefore differed from deployment before the first
prompt token. No checkpoint or metric from this directory is eligible for selection. The corrected run is
governed by `PREREGISTRATION_AMENDMENT_BOS_ALIGNMENT.md`.
