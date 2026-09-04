# Native Search Text Action v1 pre-registration

## Objective

Add one native, read-only `search_text` Action to the authoritative RWKV-LH
Harness. The Action must search workspace text without delegating operation
selection, arguments, result ranking, or urgency judgment to an auxiliary model
or external executable. RWKV remains responsible for deciding when to search,
choosing the pattern, paging, inspecting evidence, and ranking findings.

## Frozen source and data

- Source tree: the dirty WSL `UbuntuRecovered` workspace at
  `/home/chase/GitHub/RWKV-LH`; existing user changes are preserved.
- Dataset: `data/datasets/rwkv_lh_search_text_v1_cases.json`.
- Dataset source: synthetic repository fixtures written before implementation.
- Dataset version: `rwkv-lh.search-text-cases.v1`.
- Purpose: literal, regular-expression, case, Unicode, recursion, exclusion,
  empty-result, and single-file coverage.
- Generation: manually specified files and exact expected locators; no model
  output or post-run observation is used to generate expected values.

## Frozen contract

- Required: non-empty `pattern`.
- Optional: workspace-relative `path`, `mode` (`literal` or `regex`),
  `case_sensitive`, `recursive`, `max_results`, opaque `start_after`,
  `max_tokens`, `max_file_bytes`, and `max_line_chars`.
- Matching is line-oriented. Locators use one-based Unicode code-point line and
  column numbers; `end_column` is exclusive.
- Traversal is deterministic by workspace-relative POSIX path, then line,
  column, and end column.
- `.git`, `.venv`, `node_modules`, and `__pycache__` are excluded from directory
  traversal. Symlinks, binary/NUL files, invalid UTF-8, and oversized files are
  not searched and are reported as skipped.
- Cursors are opaque, query-bound, and must be copied exactly from
  `next_cursor`; a cursor from a different search contract is rejected.
- Search output is structured JSON and bounded by both `max_results` and the
  preregistered tokenizer `get_token_count` against `max_tokens`.
- The Action never assigns urgency. RWKV performs semantic prioritization from
  exact matches and may use `bind_evidence` for retained line evidence.

## Fixed evaluation

- Exact result metric: `canonical-json-locator-exact.v1`. For each dataset case,
  compare the ordered tuples `(path, line_number, column, end_column,
  match_text)` with the frozen expected tuples. Threshold: precision `1.0`,
  recall `1.0`, order accuracy `1.0` for every case.
- Pagination metric: `ordered-union-exact.v1`. Repeated pages at fixed
  `max_results=2` must equal one unpaged result with no missing or duplicate
  locator. Threshold: `1.0`.
- Token metric: the canonical output's `get_token_count` must be less than or
  equal to the requested `max_tokens` for every successful bounded-output
  case. Threshold: `1.0`.
- Boundary metric: traversal escape and cursor-contract mismatch are rejected;
  excluded/symlink/binary/invalid-UTF8/oversized inputs never yield partial
  matches. Threshold: `100%`.
- Registry metric: schema, handler, model menu, capability projection, and
  controller execution all expose the same operation. Threshold: `100%`.
- Regression: targeted search tests plus the full existing pytest suite must
  pass. A pytest capture-file failure before collection is classified as an
  environment failure and rerun with `-s`; assertion failures are never
  reclassified.

No matching rule, threshold, tokenizer, exclusion set, expected locator, or
dataset case may be changed after the first implementation run to improve the
result. Any necessary change creates v2 and records v1 as failed.
