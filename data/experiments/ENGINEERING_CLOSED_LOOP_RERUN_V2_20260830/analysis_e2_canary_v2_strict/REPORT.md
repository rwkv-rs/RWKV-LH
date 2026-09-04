# E2 canary causal-closure analysis

- engineering causal-closure gate: `True`
- strict / external / completed: 0 / 0 / 0 of 3
- raw generations / drift: 226 / 0
- binding records / drift: 413 / 0
- planned / executed / completed finalizers: 3 / 0 / 0
- child actions / network actions / backend invocations: 99 / 7 / 6
- real-scope branches not observed: `["executed_finalizer", "final_presentation_review", "failed_or_interrupted_exclusive", "supervisor_pending_recovery", "unknown_provenance_rejection"]`
- The deterministic 7/7 fault matrix and the real-model observations are reported separately; unobserved branches are not claimed as runtime coverage.
- Strict score is reported but is not used as the preregistered engineering gate.
- No RWKV raw output was modified, deleted, hidden, truncated, or reordered.
