# RWKV-LH Exact-Tool Coverage v1

This is a frozen collection plan, not a training dataset.

- 20 labels × 300 independent semantic families = 6000 cases.
- Family split is fixed at train/dev/test = 240/30/30 per label using the
  registered SHA-256 modulo rule.
- Fixtures contain mechanical ground truth and operation-specific verifiers.
- No model has been called and no raw RWKV output is present here.
- A later runner must commit raw 13.3B Executor output before parsing and may
  promote only Harness/verifier-passing attempts into the Selector pool.
