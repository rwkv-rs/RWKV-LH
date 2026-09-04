# Dual Executor profile / network G5 isolation preregistration

## Decision being tested

The completed G5 ablation rejected every checkpoint as a **global replacement**
for G3.  That result remains binding.  This experiment tests a different,
user-requested architecture: keep G3 as the offline/general Executor state and
use one separately stored G5 state for a whole network-enabled run.  A run must
select its Executor profile once from its immutable runtime policy before the
Executor lane is bootstrapped.  The profile may not change between actions.

This is not permission to merge, average, interpolate, repair, delete, reorder,
or otherwise alter RWKV output.  Selector raw logits and Executor generations
remain the only model outputs and are retained byte-for-byte.

## Frozen candidate and evidence

- General/offline profile: `EXE-G3-MULTISTAGE-STEP2000`, state SHA-256
  `13f6586951666962405286dda8e45c1eae82a37c68c21b3b75dbbb04c6e54f12`.
- Network candidate: G5 step 1500, state SHA-256
  `7392b771dd1a50a0c6d5b471a6f5c01ba1f30e7fcf59e53e74063f3c8cf744d5`.
- Step 1500 is fixed from the already-open G5 diagnostic because it is the
  earliest checkpoint at the maximum observed true-workflow score (150/240,
  58 rescues, zero regressions versus G3 on that subset).  These observed rows
  are not a confirmatory release set.
- Network Selector: S60 V7 requirement-byte-tail Head SHA-256
  `721669ce8733b590b3aa6c910d8bc13d744612f1fee884d5276a3f0d96d0d441`.
- Physical device for both models: GPU0 only.
- Sampling: temperature 0.1, top-p 1.0, top-k 0.

## Confirmatory stage A: unchanged fixed network sets

Before runtime implementation, run the already frozen live-network two-case
set and retrieval-quality nine-case set exactly once with S60 + G5 step 1500.

Stage A passes only when all of the following hold:

1. live-network E2E is 2/2 strict pass;
2. every committed S60 input has the literal complete requirement at the byte
   tail and every Executor input has `current_requirement` last;
3. retrieval quality is 9/9 across the pre-existing hard checks, including
   relevance, request binding, immutable snapshots, exact-span locators,
   Tavily-required discovery, and per-action latency <= 60 seconds;
4. no raw Selector logits or raw Executor generations are modified, deleted,
   reordered, hidden, retried, or postprocessed;
5. the existing product service on port 18070 remains healthy and unchanged.

Failure stops this candidate.  Thresholds and cases may not be weakened after
seeing the result.

## Stage B: implementation contract

Stage B is allowed only after Stage A passes.  The implementation must:

- register G3 and G5 as distinct content-addressed profiles in one pinned
  vLLM-RWKV profile manifest;
- choose G5 only when the immutable run retrieval policy is network-enabled;
  offline runs continue to use G3;
- bind the chosen profile to the Executor lane before bootstrap and keep it
  unchanged for the entire run;
- keep the 2.9B Selector state/lane independent from both Executor profiles;
- fail closed on an unknown profile, digest mismatch, mid-run profile change,
  or service identity mismatch;
- add no model retry, output normalizer, semantic correction, or case-specific
  routing rule.

## Stage C: regression and release gates

After implementation, rerun fixed offline canary, live-network two-case,
retrieval nine-case, related profile-routing tests, full project tests, and a
same-round Full90 comparison.  Offline/general runs must use G3 and show no
count or case regression against the same-round retained baseline.  Online
runs must use G5 for every Executor generation, with a single profile identity
per lane.  Only then may this be called a local network V1 candidate.

If Stage A passes but Stage C fails, retain all evidence, leave product
configuration unchanged, and report the candidate as rejected.
