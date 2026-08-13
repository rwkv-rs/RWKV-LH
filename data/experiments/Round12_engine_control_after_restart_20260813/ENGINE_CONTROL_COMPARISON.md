# Round12 engine restart comparison

This is a same-architecture engine control, not an architecture Round or Git promotion candidate.

| Run | Strict | External | Completed | FP | FN | Basic | Medium | Hard | Requests | Mean latency |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frozen_round12 | 0/90 | 11/90 | 0/90 | 0 | 11 | 10/30 | 1/30 | 0/30 | 1436 | 18225.9 ms |
| pre_restart_control | 0/90 | 2/90 | 0/90 | 0 | 2 | 2/30 | 0/30 | 0/30 | 256 | 9703.4 ms |
| post_restart_control | 0/90 | 12/90 | 0/90 | 0 | 12 | 10/30 | 1/30 | 1/30 | 1292 | 7133.0 ms |

## Interpretation

- The drop to External 2/90 before restart was an engine-instance failure: 61/90 cases failed at Goal creation. With the same frozen core after restart, External recovered to 12/90 and 83/90 Goals parsed.
- The architecture is still unsuccessful: Strict 0/90, Completed 0/90, FP 0 and FN 12. No upload gate is satisfied.
- External overlap between frozen Round12 and the post-restart control is 7 cases; 4 are frozen-only and 5 post-restart-only. The +1 total is therefore not treated as a deterministic architecture gain.

## Post-restart terminal-cause cross-tab

| Terminal cause | Cases | External correct | External wrong |
| --- | ---: | ---: | ---: |
| witness_intent_contract | 47 | 4 | 43 |
| action_argument_contract | 9 | 0 | 9 |
| action_recovery_budget_exhausted | 7 | 0 | 7 |
| goal_parse_contract | 7 | 0 | 7 |
| obligation_replan_contract | 6 | 3 | 3 |
| unhandled_priority_type | 5 | 4 | 1 |
| planning_contract | 3 | 0 | 3 |
| run_blocked_other | 3 | 1 | 2 |
| recovery_analysis_contract | 2 | 0 | 2 |
| action_choice_contract | 1 | 0 | 1 |

The next architecture variable must be preregistered from this score-independent lifecycle evidence; hidden acceptance and reference answers may not be used during generation.
