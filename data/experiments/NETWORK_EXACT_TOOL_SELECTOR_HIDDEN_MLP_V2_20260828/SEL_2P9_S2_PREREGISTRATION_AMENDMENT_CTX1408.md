# NET-SEL-2P9-S2 pre-training amendment: context 1408

Date: 2026-08-28 (Asia/Shanghai)

The authoritative RWKV-PEFT tokenizer preflight was run before training with
the preregistered `ctx_len=1280`.  It rejected 180/2,000 train rows: complete
prompt+target lengths ranged from 887 to 1,361 tokens.  No training process was
started and no model result was observed.

The failed contract is preserved as `INVALID_ctx1280`.  To keep every target
suffix intact, S2 changes only `ctx_len` from 1,280 to 1,408, the next fixed
32-token-aligned value above the measured maximum.  Dataset rows, order,
labels, ratios, zero-state parent, 2,000 steps, seed, LR schedule, checkpoint
selection, MLP configuration, external holdout, metrics and thresholds remain
unchanged.  Both train and dev must pass the 1,408-token contract before the
training service may start.
