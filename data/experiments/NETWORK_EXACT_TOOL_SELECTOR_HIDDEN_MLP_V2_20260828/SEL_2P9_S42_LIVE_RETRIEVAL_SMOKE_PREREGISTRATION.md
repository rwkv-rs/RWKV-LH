# SEL-2P9-S42 live retrieval smoke preregistration

## Purpose

Confirm that the newly activated fixed 25-class product menu is backed by a
real local retrieval Harness, not merely a correct `web_search` classification.
This smoke calls only the retrieval action boundary; it does not ask RWKV to
generate arguments, does not invoke the 13.3B Executor, and does not alter any
RWKV output.

## Frozen request and policy

- action: `web_search`;
- exact arguments:
  `{"query":"RWKV official GitHub repository","max_results":3}`;
- immutable run policy: `auto_public`, no workspace egress approval;
- product Harness uses the fixed-menu mode, so its executable catalog must be
  exactly the 23 canonical classes excluding `final_answer` and `ABSTAIN`;
- snapshot/output root:
  `data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828/run_s42_live_retrieval_smoke`;
- discovery order remains project-owned Tavily, then Bing RSS, then
  DuckDuckGo; configured API keys are read from `.env.local` but their values
  must never be written to stdout or experiment artifacts.

## Gates

The one-shot smoke passes only if:

1. `.env.local` contains at least one configured Tavily credential;
2. the exact 23-operation menu is present with `web_search` and
   `connector_lookup` and without planner/final classes;
3. the unchanged network policy authorizes the fixed public literal without
   rewriting arguments;
4. Tavily reports a successful credential attempt and commits at least one
   independently fetched public page;
5. the Harness returns `evidence_committed`, at least one content-addressed
   evidence record, exact spans, and immutable snapshots/routes;
6. no secret value appears in the report, provider attempt summary, evidence,
   or stdout;
7. retries at the agent/Harness level, fallback tools, RWKV generation, output
   postprocessing, tool re-selection, and Executor calls are zero.

Failure is recorded without changing provider order, query, policy, or result
criteria. A provider-level credential rotation already implemented inside the
single Tavily call is retained as provider evidence and is not an agent retry.
