# Initial canary aborted

The initial `variant_b_contract_graph` run was manually stopped after
`ECRA-ROUTE-001` and `ECRA-ROUTE-031` established the failure mode.

- `ECRA-ROUTE-001`: first tool `list_directory`, exact, completed.
- `ECRA-ROUTE-031`: first tool `web_search`, exact; the synthetic backend returned
  only a route marker, so the independent factual Reviewer correctly considered
  the weather obligation insufficient. The correction graph repeated
  `web_search` and interrupted with `contract_graph_correction_repeated`.
- Root cause: the benchmark prompt asked the full factual task while the frozen
  backend intentionally contains no factual web corpus. Content adequacy therefore
  contaminated the route-only metric.
- Scope: all public-web, connector and mixed cases using the route-only backend.
- Resolution for r2: wrap the unchanged original task in an explicit route-only
  evaluation contract. A successful synthetic envelope or a typed privacy rejection
  satisfies the route probe; factual answer quality remains out of scope. The dataset,
  expected actions, metrics and thresholds are unchanged.

The partial directory is retained as invalid diagnostic evidence and must not be
used as a benchmark result.

## r2 diagnostic

`variant_b_contract_graph_r2` was also stopped after `ECRA-ROUTE-001` exposed a
second, independent harness gap. RWKV again selected `list_directory` exactly,
but the Planner's no-network obligation could not be proven from positive action
capsules. The Reviewer correctly refused to infer absence from missing evidence,
causing three repeated local listings and `contract_graph_correction_repeated`.

The systemic resolution is a Controller-authored `network_audit` result capsule
folded mechanically from committed atom operation results. It records attempted
network operations, policy decisions, backend-invocation count and the zero-action
case without model testimony or query rewriting. r3 must retain the same dataset,
answers, route wrapper, metrics and thresholds.

## r3 diagnostic

`variant_b_contract_graph_r3` proved the Controller audit is visible and usable:
the Reviewer cited its evidence ID and, in one round, marked the no-network
obligation satisfied. The run still interrupted because the v1 route-only wrapper
described successful synthetic evidence and typed rejection in adjacent sentences;
the Planner compiled them as conjunctive obligations even for a local-only task.

r4 changes only this ambiguous benchmark wrapper to three explicitly mutually
exclusive completion branches: local/deterministic with zero-network audit,
permitted network with one synthetic envelope, or rejected network with one typed
rejection and zero backend invocation. Inapplicable branches must not become
obligations. Dataset answers, original task text, architecture and thresholds remain
unchanged.

## r4 diagnostic

`variant_b_contract_graph_r4` compiled the correct two obligations, and every
Reviewer round marked both the root listing and zero-network requirement satisfied.
The finalizer still never ran because `network_audit.workspace_revision` incorrectly
included the total causal-event count. Committing a Review changed that count,
therefore changed the audit evidence ID and aggregate evidence digest; the next loop
could never find a Review matching the newly computed digest and issued another one.

r5 makes the network-audit capsule identity depend only on its audit content. Review
events no longer invalidate the facts they reviewed. No model prompt, dataset answer,
tool result, metric or threshold changes.
