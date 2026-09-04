# Selector zero-State Head v3

Date: 2026-09-04

Purpose: deploy the existing zero-State Selector Head under the current 23-executable-class runtime without training and without a legacy runtime branch.

Method: remove only the `final_answer` and `ABSTAIN` output rows from the registered 25-class artifact. The retained 23 `head_weight` rows and 23 `head_bias` values are byte-for-byte equal as parsed JSON values. Shared feature normalization, shared MLP, layer normalization, and temperature are unchanged.

The artifact records its old training input and trajectory as source provenance. Its current runtime contract is `selector-intent.v2`, `fresh-current-subtask.v1`, zero-State, and 23 executable classes.

This projection does not claim v2-distribution training or improved accuracy. It exists only as the no-training baseline requested before StateTune.

Source artifact:

```text
data/experiments/RWKV_LH_G1J_SELECTOR_HEAD_V2_20260904/selector_intent/head/selector_head.json
file sha256: 49538a32162941a256f1075ea465b52bda5ddc07e9e4001f94268f7c4368892a
head hash: ef83fd7bf9340977f2ae16d95899690addf3446467ea43a138c61f0926c69bdd
```

Current artifact identity is recorded in `MANIFEST.json`. `training_performed` and `state_tuned` are both false.
