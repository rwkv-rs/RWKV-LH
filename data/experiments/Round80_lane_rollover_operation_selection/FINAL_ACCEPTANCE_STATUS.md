# Round80 final acceptance status

Status: **three implementation/measurement stages complete; overall acceptance failed**.

Completed:

- frozen rollover and operation-selection protocol;
- `long-horizon.run.v13`, zero-semantic-call general rollover and exact manifests;
- independent 30-case/90-request real selector benchmark;
- real forced rollover probe;
- final code unit 77/77, control 40/40, E2E catalog 90/90;
- final full90 r2 90/90 cases with complete audit artifacts;
- final causal and persistence invariant audit.

Acceptance failures:

- operation exact `47/90 = 52.22%`, below 90%;
- full90 Strict `0/90`, External `10/90`, Agent `1/90`, FP `1`, FN `10`;
- 26 accumulated-lane candidates bypassed `lh_select_operation` and 33 used wrong wire keys;
- M06 and the larger completion/repair paths remain unsuccessful.

Architecture evidence that did pass:

- 38/38 final full90 rollover records valid across 30 cases;
- 0 context-limit failures;
- old checkpoint bytes/digests preserved and 652 archived events explicitly accounted for;
- storage reduced from 19.96 GB incomplete r1 to 0.94 GB complete r2 without changing model output or verifier scoring.

Therefore Round80 does not replace the Round46 baseline and does not support a “real usable” claim. The remaining work is now isolated to operation/phase semantic stability and downstream completion/repair recall rather than context overflow or hidden state loss.
