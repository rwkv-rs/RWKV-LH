# NET-SEL-2P9-S33 mean-last fusion zero-state head result

Date: 2026-08-28 (Asia/Shanghai)

Decision: **direction confirmed, candidates rejected by the preregistered
development conjunction**.  Same-forward feature fusion materially improves
the route, but neither registered width passes every per-class gate.  No head
is locked, S30 blind remains sealed, and no production source or state profile
is changed.

## Architecture and integrity

- current direct `LongHorizonModel -> Harness` architecture;
- independent 2.9B Selector over all 25 exact classes and unchanged persistent
  13.3B Executor responsibilities;
- physical GPU0, zero Selector state, compact V3, unchanged model weights;
- one deterministic 5,120-dimensional vector:
  `current-step mean[2560] || current-step last[2560]`;
- both views came from the same already frozen current forward; additional
  RWKV forwards: 0;
- source weights restored to S28=`1`, S30=`1`;
- S28/S30 test rows skipped before JSON parsing: `750/500`; test-label access
  and test metrics: 0;
- generated RWKV text, sampling, masks, repair, retry, postprocessing, and
  Executor fallback: 0;
- the derived protocol was registered only in the experiment process; the
  product loader/service remains unchanged.

Preregistration SHA-256:
`08980d86c564761e9f39549d6d68f7ac25a7220da1b68506a4a5bedac2c6b3c2`.
Trainer SHA-256:
`7e57db2c96dbff58683aa66781d567b3ac48f38d000e2a7bfb38862688127323`.

## Development results

| candidate | S28 exact | S30 exact | S30 macro-F1 | EN | ZH | failed gate |
|---|---:|---:|---:|---:|---:|---|
| `concat-h256` | 749/750 | 491/500 | 0.981911 | 241/250 | 250/250 | `file_digest` recall 17/20 |
| `concat-h512` | 750/750 | 492/500 | 0.983743 | 242/250 | 250/250 | `file_digest` and `read_file` recall 17/20; read boundary 37/40 |

`concat-h256` passed every other registered gate, including both languages,
all stages, all six sibling boundaries, future distractors, S28 retention,
portable replay, and integrity.  Its `read_file/read_json` boundary reached the
minimum exactly at `38/40`.  `concat-h512` obtained the highest aggregate score
but cannot override its failed per-class and boundary gates.

Compared with mean-only S30 (`486/500`, English `237/250`), same-forward fusion
rescued five or six total decisions and raised English to `96.4%`/`96.8%`.
All Chinese dev decisions are correct.  The remaining h256 errors are nine
English cases; three are `file_digest` continuation decisions after a prior
`list_directory` action.  The errors are not hidden by the aggregate 98.2%.

Machine-readable selection SHA-256:
`81aa8cc4d881f5e8e098387cdbc1363c9ca2facda2ef1a495a61d0e27bb986fe`.
The `concat-h256` / `concat-h512` head hashes are respectively
`6b8a9852e01f52aab6d2b416237de64591ebad6a975f2b1d09536cd985dada6d`
and
`4002523e70cd3903295f1e5b6ee940e3e730a599b2b85a5d96f3371f54a6c03f`.

## Interpretation and next bounded test

S33 supplies causal evidence that a single mean view was discarding useful
latest-step information; concatenation is the first architecture in this line
to clear 96% independently in both languages while retaining all 25 classes.
The smaller h256 head satisfies more robustness gates than h512 despite one
fewer aggregate correct decision.  This pattern supports a bounded capacity
regularization ablation before changing data, loss, or state: train only
smaller fused h64/h128 heads under the identical zero-state protocol and
unchanged loss, choosing the smallest passing head.  That test must be
separately preregistered and cannot read blind unless every existing gate
passes.
