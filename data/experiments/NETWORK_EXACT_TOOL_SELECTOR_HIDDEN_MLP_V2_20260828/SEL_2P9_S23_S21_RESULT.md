# NET-SEL-2P9-S23 S21 result

Date: 2026-08-28 (Asia/Shanghai)

S21 is rejected for the current direct-Harness architecture.

- fixed decision points: 245 (`first=120`, `continuation=125`);
- historical 13.3B direct route: 182/245 = 0.742857;
- S21 persistent 2.9B route: 4/245 = 0.016327;
- S21 selected `current_time` on all 245 rows;
- local network false takeovers remained zero, but required-online false
  negatives were 69 versus the historical baseline's 4;
- raw 25 logits and raw argmax were retained; generation, sampling,
  postprocessing and Executor fallback were all zero;
- physical device: GPU0;
- result SHA-256:
  `5a0504cd3366c3ee5b59ea441845f078a394ddae3db2a6141d07dd5e9839bb54`.

Root cause: S21 learned mean-hidden geometry for standalone
`SelectorObjectiveV4` strings.  The deployed causal lane first processes the
task and 25-description menu, then exposes a current-step mean hidden while
preserving the recurrent state.  That representation is outside S21's training
distribution and collapses to one class.  No threshold or output repair is
authorized.  The next candidate must be trained on the exact current-Harness
bootstrap/step/state boundary and re-evaluated against the unchanged S23 set.

