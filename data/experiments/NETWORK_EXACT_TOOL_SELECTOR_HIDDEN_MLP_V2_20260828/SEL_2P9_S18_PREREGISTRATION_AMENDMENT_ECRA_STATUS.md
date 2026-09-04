# S18 amendment: ECRA120 evaluation status

Date: 2026-08-28 (Asia/Shanghai)

This amendment is recorded before the S18 head is evaluated on ECRA120.  It
does not change any metric, threshold, model, row, menu or decision rule.

The S18 preregistration called ECRA120 a still-unread external holdout.  That is
incorrect at the artifact lineage level: the upstream S8 head was evaluated on
the complete ECRA120 in the earlier rejected S9 function-takeover experiment.
S18 itself has not read or trained on ECRA, but its parent artifact has, and the
historical connector-takeover failure is known.

Therefore:

- ECRA120 keeps every already registered S17/S2 threshold and is run once as a
  fixed historical regression, not reported as a blind holdout;
- no ECRA result may change S18 weights, head, menus, thresholds or fusion;
- an ECRA pass authorizes implementation/shadow work only;
- active routing additionally requires a protocol-frozen fresh live canary and
  its complete local/Harness/state-isolation/crash-recovery regression; those
  cases must be created after the S18 implementation contract is frozen and
  before any live Selector call;
- both passing and failing ECRA/live raw outputs remain append-only.

The original preregistration and its inaccurate phrase remain preserved.  This
amendment supplies the authoritative evaluation-status correction rather than
rewriting history.
