# RWKV action-state tuning seed v1 preregistration

- Date: 2026-08-26 (Asia/Shanghai)
- Protocol: `rwkv-lh.action-state-tuning-seed.v1`
- Purpose: freeze non-evaluation synthesis seeds for the current progressive G1i
  action protocol before producing any expanded training corpus.

## Data boundary

1. `rwkv_lh_ecra_route_v1`, RWKV-E2E-90, their reference answers, hidden
   acceptance files, and R9 case traces are evaluation/diagnostic holdouts. Their
   task text must not become training text or be supplied to a synthesis model.
2. The historical `rwkv_lh_operation_selection_v1` dataset targets the deleted
   `lh_select_operation` protocol and must not be converted into positive examples.
3. R9 Strong Planner schema failures are not RWKV action-state examples. Planner
   contract data must remain in a different corpus and optimization run.
4. Only Controller-verified action/result segments may become positive trajectory
   examples. Failed outputs remain rejection metadata until a verified corrected
   continuation exists.

## Frozen seed behavior

The seed inventory covers these systemic boundaries:

- exact file target versus directory discovery;
- text versus JSON reads;
- public web versus structured connector lookup;
- deterministic compute/clock versus network retrieval;
- Observation-to-next-argument literal binding;
- privacy and untrusted-output calls reaching the Network Gate without backend
  execution or query rewriting;
- zero-progress repetition suppression;
- protocol-rejection correction with the selected tool contract retained;
- provider-unavailable honest termination rather than blind replay;
- inspect/mutate/verify transactions;
- check-only versus mutating command choice;
- final answer only after required evidence exists.

Every generated action turn must train the exact current wire boundary:

1. progressive selector output:
   `{"function":"select_tool","params":{"name":"<operation>"}}`;
2. after Controller disclosure, one complete direct call for the same operation;
3. subsequent decisions consume the exact Controller-produced ModelEvent body;
4. no rationale, classifier label, invented observation, or Controller-owned
   semantic field is included in the model target.

## Generation and acceptance

- Seed blueprints contain no copied evaluation request.
- Expanded records must use newly generated paths, entities, numbers, languages,
  phrasing, file contents, and branch structures.
- Deduplicate training requests internally and against all holdout instructions.
- Registered contamination metric: `utf8-byte-ngram-cosine.v1`, UTF-8 byte
  5-gram cosine. Exact overlap must be zero and maximum similarity to a holdout
  request must be below `0.75`.
- Split by semantic template/entity family before rendering, not by shuffled rows.
- Recommended minimum expansion is recorded per seed; it is a generation target,
  not a claim that the expanded corpus already exists.
- The generated seed package must record source, version, purpose, generator,
  file digests, tool-contract digest, and holdout file digests.
