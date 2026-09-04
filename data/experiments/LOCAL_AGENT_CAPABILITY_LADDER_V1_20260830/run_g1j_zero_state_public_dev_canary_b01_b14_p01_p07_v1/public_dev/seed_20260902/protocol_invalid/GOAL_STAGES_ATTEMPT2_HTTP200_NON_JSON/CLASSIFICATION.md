# GOAL_STAGES_ATTEMPT2_HTTP200_NON_JSON

- Classification: protocol-diagnostic; excluded from capability scoring pending raw response inspection.
- Time: 2026-09-02T12:27:52Z.
- Strong Planner requests: 1.
- HTTP result: 200.
- Parser result: `SupervisorProtocolError: supervisor content is not one JSON object`.
- RWKV model requests: 0.
- Tool actions: 0.
- Hidden retries: 0.

The transport succeeded, but the returned assistant content did not match the current single-object decoder. The next diagnostic captures the actual response envelope before deciding whether the request or the transport-only normalizer is wrong.
