# NET-SEL-2P9-S14-OBJECTIVE-GATE preregistration

Date: 2026-08-28 (Asia/Shanghai)

## Trigger and architecture

S11 full-mean preserves online quality but has 12 Gate false takeovers. S13
compact data changes which local rows fail without reducing the total and loses
Tool quality when the natural online supplement is removed. The registered S11
last-hidden diagnostic defers 60% of required online rows. Continuing to add
surface templates to the same full-mean representation is therefore stopped.

S14 tests a representation-level split while preserving one 2.9B RWKV forward:

- Gate receives a causal objective-prefix mean, or the concatenation of that
  prefix mean and the complete-input mean;
- Tool uses the frozen S11 selected mean normalizer and Tool MLP exactly;
- raw argmax remains the only decision operation;
- Selector state is zero and Executor profile `NET-EXE-13P3-N0` is unchanged.

The full input still contains task, progress and tool names/descriptions, with
no schemas or results. Prefix pooling changes only which already-produced
hidden rows feed the Gate; it neither removes the menu from the RWKV input nor
invokes a second forward.

## Fixed data and selection

Gate uses the frozen 2,000-row S13 dataset SHA-256
`47ce71fd807bfb5788578190a844c9560f961de1d48ce71244130fcbcc6be22e`.
Tool weights and normalizer come from S11 artifact SHA-256
`31f68ed76c8ff1db8a68b2b7943f231e2ff70b2232d99d9ce486bb02c06ff361`.

For each canonical input, the prefix ends after the complete JSON-encoded
`objective` value. Its token span is the longest common token prefix between
the independently tokenized prefix text and full text; it must contain at least
four tokens and may not exceed the full row. Padding is excluded.

Train two Gate candidates with the unchanged seed 841, hidden width 256,
dropout 0.2, AdamW parameters, class weights, epoch limit and patience:

1. 2,560-d prefix mean;
2. 5,120-d `[prefix_mean, full_mean]` concatenation.

Select by dev Gate macro-F1, then dev loss, then prefix before concat. S13 test
Gate accuracy/macro-F1 must be >=0.95 and DEFER recall >=0.97; all compact dev
clusters must be exact. S11 frozen Tool internal metrics are inherited only
after its tensor identity is verified.

## External gates

The unchanged complete ECRA120 boundary must pass: web >=23/25, connector
>=18/20, required online non-takeover <=10%, web/connector macro-F1 >=0.90,
and zero takeovers in all local, deterministic, mixed-local-first and privacy
rows. Relative to S11 it must rescue all 12 false takeovers, add none and
regress no required-online exact row. Passing permits, but does not replace,
full Harness and live-retrieval regression before integration.

