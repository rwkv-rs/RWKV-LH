# Round12 formal durable transport manifest

This metadata-only audit does not read prompts, model responses, benchmark acceptance, or reference answers.

| Check | Result |
|---|---|
| `formal_results_have_90_rows` | PASS |
| `one_transport_job_per_reported_model_request` | PASS |
| `started_returned_delivered_remote_job_ids_match` | PASS |
| `every_remote_job_complete_http_200` | PASS |
| `every_remote_job_invoked_rwkv_exactly_once` | PASS |
| `every_local_delivery_reports_one_upstream_invocation` | PASS |
| `every_job_delivered_on_one_transport_attempt` | PASS |
| `no_transport_or_delivery_failure_events` | PASS |
| `all_request_hashes_match_remote` | PASS |
| `all_response_hashes_and_sizes_match_remote` | PASS |

Overall: **PASS**.

- Formal result rows: 90
- Reported model requests / remote jobs: 1436 / 1436
- Transport failure events: 0
- Every remote upstream invocation count was exactly one: True
