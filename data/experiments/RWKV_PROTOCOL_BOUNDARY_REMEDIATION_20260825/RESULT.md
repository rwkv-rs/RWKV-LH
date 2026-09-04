# RWKV protocol-boundary remediation result

- Date: 2026-08-25
- Protocol: `rwkv-protocol-boundary-remediation.v1`
- Registered metric: exact structural equality
- Required threshold: `1.0`
- Observed score: `1.0`
- Outcome: passed

## Root causes and system impact

1. Rollover stored retained event IDs independently from reconstructed prompt
   bytes. Both prompt-replay and native-state transports could therefore claim an
   event was visible while omitting its body. The rebuilt state now renders the
   retained `ModelEvent` objects first and derives `visible_event_ids` from those
   exact objects. A latest protocol rejection is mandatory during bounded fallback.
2. External evidence validated its own route structure but was not bound at the
   common action boundary to the currently selected tool and normalized arguments.
   One shared digest validator now covers frozen, live-cache, execute and recovery
   paths; mismatches fail closed and never become evidence.
3. Ordered `text_template` accepted an ambiguous sort protocol. Contract creation
   now requires exactly one object-list source and one sort key, while unordered
   templates must leave keys empty. The planner prompt exposes the same rule.
4. Unordered template matching greedily consumed the first substring occurrence.
   It now enumerates candidate intervals and performs deterministic,
   quantity-preserving, non-overlapping backtracking. Search exhaustion returns an
   insufficient verdict instead of a false contradiction.

The affected downstream surfaces are RWKV retry correction, decision visibility
audits, immutable retrieval recovery, typed contract acceptance, and supervisor
contract generation. RWKV remains the only action/final-answer authority; the new
logic only preserves deterministic state and validates execution evidence.

## Validation record

- Python compilation of changed runtime and test modules: passed.
- First focused run: 119 passed, 1 failed. The failure exposed that recovery
  wrapped a binding mismatch as a generic recovery error; the action boundary was
  corrected to preserve the typed fail-closed result.
- Final focused run:
  `uv run pytest -q -s tests/test_model_session.py tests/test_unified_controller.py tests/test_retrieval_harness.py tests/test_retrieval_kernel.py tests/test_contract_graph.py`
  — 120 passed in 20.05 seconds.
- Full repository run: `uv run pytest -q -s` — 253 passed in 51.16 seconds.
- `git diff --check`: passed.

## Registered regression coverage

- Prompt-replay and native-state rollover contain rejection error bodies.
- Rejected arguments and selected operation remain visible after rollover.
- Retained event IDs equal the events actually rendered into the rebuilt state.
- Execute and recovery reject envelopes produced for different arguments.
- Misplaced live route files do not fall through to a provider request.
- Ordered templates reject zero/multiple sort keys.
- Prefix/subsequence templates and duplicate multiplicity use distinct,
  non-overlapping occurrences.

No generated dataset, subjective scoring, threshold change or case-specific
production branch was introduced.
