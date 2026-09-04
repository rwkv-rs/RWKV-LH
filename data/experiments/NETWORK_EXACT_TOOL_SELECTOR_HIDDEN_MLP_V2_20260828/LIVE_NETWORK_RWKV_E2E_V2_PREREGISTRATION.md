# Live-network RWKV E2E V2 preregistration

Frozen on 2026-08-29 (Asia/Shanghai), before EXE-G6 data generation, training,
checkpoint evaluation, or any V2 live run.

## Purpose

V1 exposed one general Executor defect: after a valid network observation, a
workspace write used an absolute path; after the Harness rejected it, the model
repeated or structurally worsened the call. V2 is an unseen release holdout for
the complete independent Selector/Executor architecture. It is not training
data and none of its exact requests, paths, entity names, URLs, or expected
values may appear in EXE-G6 train or dev data.

## Frozen cases and checks

Six public-network tasks cover exact-URL discovery, public-web discovery,
GitHub repository metadata, PyPI package metadata, Crossref scholarly metadata,
and current weather. Each task requires at least one committed external-evidence
action and a nested workspace-relative output path. The evaluator requires:

1. the run reaches the persisted completed state;
2. every required network operation succeeds and commits at least one immutable
   external-evidence record;
3. the requested artifact exists, is valid UTF-8 text or JSON, and satisfies
   all fixed field/content contracts;
4. every non-empty output field marked `grounded` occurs in the serialized
   committed network evidence for that run;
5. the append-only audit chain is valid, every returned generation retains its
   original raw bytes and token IDs, and no generation is marked postprocessed;
6. the independent Executor input satisfies the request/question-at-tail
   protocol for every generation;
7. no state profile is switched after task/lane creation.

The aggregate gate is 6/6. One attempt is used with temperature 0.1, top-p 1,
top-k 0, and the first raw output. Retrieval content is live but becomes an
immutable per-run snapshot. No controller repair, hidden retry, semantic
postprocessing, output rewriting, or acceptance of absolute workspace paths is
allowed.

## Leakage and similarity rule

The G6 generator must compare every new train/dev request with every V1 and V2
holdout request using byte 5-gram cosine similarity. The maximum must remain
below 0.75. The metric and threshold are fixed before data generation and may
not be changed after observing a result.
