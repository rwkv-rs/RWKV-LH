# NET-SEL-2P9-S17 scoped variable-menu description scorer preregistration

Date: 2026-08-28 (Asia/Shanghai)

## Root question

The strong Planner authors an atom kind/effect ceiling but never names a
concrete operation.  Controller capability projection and `ScopedAtomHarness`
then expose only operations authorized for that atom.  S5-S8 nevertheless
evaluated the pairwise description scorer as a global fixed 25-way classifier,
including operations that would not appear in the real atom menu.

S17 asks whether the already frozen S8 shared scorer passes when used according
to the actual Harness boundary: score each displayed name/description and take
raw argmax only over that immutable displayed menu.  Pair scores are independent
of menu cardinality, so projecting the already stored 25 raw pair scores onto a
predeclared menu is numerically identical to scoring only those descriptions.
The complete source logits remain preserved in the experiment record; no score
is changed, thresholded, repaired or reranked.

## Frozen candidate and data

- S8 head SHA-256
  `36728736ce539039f5af132872edbf0f179aa66112ce57dbf16a578cf2586c23`;
- zero learned initial state; 2.9B last-real-token query features;
- S6/S8 frozen rows and raw 25 pair scores; no retraining;
- S8 test = 750 rows, registered natural dev = 176 rows;
- ECRA120 stays unopened until the scoped internal gates pass;
- generated RWKV text and sampling invocations remain zero.

## Mechanical menu families

Menu family is derived from the expected operation's authoritative capability
class only to isolate Selector quality conditional on a correct Planner
capability domain.  It never reduces a menu to the expected operation.

- read/public-read work: all local workspace reads, deterministic operations,
  `web_search`, `connector_lookup`, `final_answer`, `ABSTAIN`;
- workspace mutation: local workspace reads, deterministic operations, all
  workspace mutations, `final_answer`, `ABSTAIN`; no network/process action;
- local-process read: read/public-read menu plus `check_command`;
- local-process mutation: every registered executable operation plus
  `final_answer`, `ABSTAIN`;
- finalizer: local workspace reads plus `final_answer`, `ABSTAIN`;
- abstention boundary: complete 25-label menu.

Every expected label must be present.  The exact ordered menu and digest are
stored with each prediction.  For ECRA120 all six registered route categories
use the same read/public-read work menu; therefore no ECRA answer or category
can choose a narrower menu.

## Fixed gates

Internal S8 gates are unchanged after scoped raw argmax:

- test accuracy and macro-F1 >= 0.90;
- every class recall >= 0.75;
- web/connector/calculator/date/time recall >= 0.85;
- boundary accuracy >= 0.85;
- natural dev overall >= 0.90 and every registered cluster >= 0.80.

Only if all pass may the unchanged ECRA120 run once.  ECRA gates remain the S2
registered exact first-tool/category thresholds, local network false positives
zero, required-online false-negative <= 0.10 and web/connector macro-F1 >= 0.70.

Passing authorizes a variable-menu protocol/service implementation and shadow
canary only.  Active product wiring additionally requires exact menu authority,
unmodified raw-score retention, state-lane isolation, crash recovery, real
2.9B-to-13.3B handoff, live networking and the full local suite.  Failure
rejects S17 without changing S8 or any existing runtime.
