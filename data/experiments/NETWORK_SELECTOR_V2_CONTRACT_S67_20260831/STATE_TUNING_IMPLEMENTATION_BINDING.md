# S67 state full-dev implementation binding

This binding is frozen after the already preregistered ST500 screen result was recorded and before any retention feature is extracted or any full-retention metric is read. It applies only to full-dev implementation details already constrained by `STATE_TUNING_PREREGISTRATION.md`; it does not change a screen result, dataset, threshold, metric, checkpoint order, or selection rule.

- A frozen-S66 branch consumes the same state-conditioned mean+last hidden used by the S67 expert. This preserves the one-RWKV-extraction contract. Its weights and original zero-state normalization remain frozen.
- Every `baseline-correct regression`, S60 source delta, retention MSE target, and preserved-margin target is measured against the released S66 head evaluated on the already frozen zero-state features. A state-shifted S66 branch is not allowed to redefine the accepted baseline.
- `ST-FROZEN-CASCADE` uses `frozen_s66(state_hidden) + sigmoid(gate(state_hidden)) * (s67_expert(state_hidden) - frozen_s66(state_hidden))`. The h64 gate uses the S67-state train mean/std and the preregistered C3 loss weights `5/1/10`.
- If the frozen cascade fails, `ST-PAIRED-CASCADE` trains its h128 retention expert on S65 state features normalized by S65-state train mean/std. Its loss is true-label CE plus `0.5 *` raw-logit MSE to released S66 on zero-state S65 features. The S67 expert remains the exact screened head and its S67-state normalization remains unchanged.
- The paired raw-logit formula is `retention_expert(state_hidden) + sigmoid(gate(s67_normalized_state_hidden)) * (s67_expert(state_hidden) - retention_expert(state_hidden))`. The h64 gate again uses the preregistered C3 optimizer and `5/1/10` domain/MSE/margin weights; retention targets remain released zero-state S66 logits.
- Mean/last hidden, branch logits, gate logits, and final logits are preserved as produced. There is no rule mask, threshold route, argmax repair, logit postprocessing, generated RWKV text, or sampling.
- Full-dev acceptance and checkpoint progression remain exactly those in the preregistration. Locked-test stays unavailable until one unique dev candidate is frozen.
