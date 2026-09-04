# E3 canary causal-closure analysis

- engineering causal-closure gate: `True`
- strict / external / completed: 0 / 0 / 0 of 1
- raw generations / drift: 50 / 0
- binding records / drift: 82 / 0
- planned / executed / completed finalizers: 2 / 0 / 0
- child actions / network actions / backend invocations: 21 / 0 / 0
- real-scope branches not observed: `["executed_finalizer", "final_presentation_review", "failed_or_interrupted_exclusive", "supervisor_pending_recovery", "unknown_provenance_rejection"]`
- The deterministic 7/7 fault matrix and the real-model observations are reported separately; unobserved branches are not claimed as runtime coverage.
- Strict score is reported but is not used as the preregistered engineering gate.
- No RWKV raw output was modified, deleted, hidden, truncated, or reordered.
