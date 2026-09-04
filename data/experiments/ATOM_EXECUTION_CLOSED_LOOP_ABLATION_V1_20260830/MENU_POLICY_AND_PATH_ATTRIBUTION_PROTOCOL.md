# Menu policy and path-operation attribution protocol

Date: 2026-08-30

## Purpose

Separate two possible engineering effects from model capability on the fixed B
arm before changing any Selector or Executor state:

1. network operations that were incorrectly eligible for an immutable offline
   Goal; and
2. JSON mutation operations selected for contracts whose declared write roots
   are not unambiguously JSON paths.

This is a read-only diagnosis, not a new architecture ablation.  It does not
change the frozen evaluation dataset, output, raw RWKV generations, thresholds,
or scoring algorithm.

## Frozen source

- Dataset: `rwkv_agent_capability_ladder_v1`, version `v1`, 10 cases.
- Dataset purpose: fixed real Planner-Selector-Executor-Harness holdout.
- Dataset generation: `scripts/generate_agent_capability_ladder_v1.py`.
- B-arm result: `run_b_contract_progress_v1/results.json`.
- B-arm result SHA-256:
  `2f2369153ee69bad7a1bfc1da5fa024cf523e6664ed38adb25ccc024171207f1`.
- Execution freeze SHA-256:
  `9d107b1c8c2454d4aef0c49f3c8acf5a57a92ab4e904abc5f3626b7442bffc46`.
- Prior strict diagnosis SHA-256:
  `9303b8f8e6151c57618291d2edfd7bfb04d8d81654f439a7013768f035aaeaf9`.
- State stores must be opened with SQLite `mode=ro&immutable=1`; the
  `LongHorizonStore` API is forbidden for this analysis.

## Fixed algorithms

### Offline eligibility counterfactual

For every stored exact Selector record in a case whose frozen retrieval mode is
`offline`:

1. preserve the stored 25-class order and every raw logit byte;
2. remove only labels whose authoritative network access is `public_web` or
   `structured_source` (`web_search`, `connector_lookup`) from the stored
   eligible set;
3. choose the greatest remaining raw logit, breaking ties by the earliest class
   index, exactly matching `eligible_raw_logit_argmax`;
4. report the stored selection and counterfactual selection.  Do not replay or
   infer downstream actions from a changed selection.

Cases with `auto_public` remain unchanged and form the policy control group.

### Write-root classification

Normalize `/` separators without changing path text.  For every mutate atom:

- `json_only`: every declared non-empty root is a concrete path ending in
  `.json` case-insensitively;
- `non_json_only`: every declared root has a non-empty suffix other than
  `.json`;
- `ambiguous_or_mixed`: a root is `.`, has no suffix, or JSON and non-JSON roots
  are mixed.

For `write_json` and `patch_json`, report declared-root class, exact action path
suffix, success, workspace change, and whether `write_file` or `replace_text`
was also stored as eligible.  Path suffix is diagnostic only: no operation may
be masked unless an authoritative ActionDefinition or atom media-type contract
declares that constraint.  This prevents a controller heuristic from hiding a
real Selector weakness.

## Integrity and outputs

- Strict RFC-compatible JSON (`allow_nan=False`).
- Exact counters only; no subjective similarity judgement.
- Recompute and record hashes for every audit and immutable worker database
  read, the analysis script, protocol, result, and report.
- Assert stored raw Selector records are unchanged and their selected operation
  equals the stored eligible raw-logit argmax.
- Write a new versioned output directory; never overwrite V1/V2 analyses.

## Pre-registered interpretation

- Any offline network selection is an engineering eligibility defect, because
  execution is deterministically forbidden by the same Goal.
- The counterfactual quantifies only the immediate selection that the corrected
  mask would have produced; it is not counted as an end-to-end pass.
- JSON-operation/path correlation informs state-tuning data.  It does not
  justify suffix-based masking without authoritative schema metadata.
- Remaining failures after the policy fix and bounded evidence/input fixes are
  eligible evidence for separate 2.9B Selector and 13.3B Executor state tuning.
