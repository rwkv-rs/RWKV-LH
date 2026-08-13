# Round12 durable transport gate

This is an infrastructure-only, non-scoring gate. It reads job ids, byte counts, hashes, states, and invocation counts only; it does not read prompt/response content, benchmark data, acceptance rules, or reference answers.

| Check | Result |
|---|---|
| `all_17_jobs_present_locally_and_remotely` | PASS |
| `all_remote_states_complete` | PASS |
| `all_remote_upstream_invocations_exactly_one` | PASS |
| `all_delivered_response_hashes_match_remote` | PASS |
| `same_request_eight_distinct_jobs_not_deduplicated` | PASS |
| `single_forced_disconnect_recovered_without_regeneration` | PASS |
| `eight_simultaneous_disconnects_recovered_without_regeneration` | PASS |

Overall: **PASS**.

- Jobs: 17
- Forced retrieval interruptions: 9
- Every legitimate job invoked upstream RWKV exactly once: True
- Every delivered raw response SHA matched the remote persisted response SHA: True
