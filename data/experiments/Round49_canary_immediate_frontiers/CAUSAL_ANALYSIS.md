# Round49 Canary Causal Analysis

## Frozen outcome

The fixed canary produced Strict `0/10`, external acceptance `1/10`, and agent
completion `4/10`. The preregistered gate failed decisively. Basic30 must not
run and the candidate is not retain/upload-eligible.

## First causal failure

The authoritative frontier rule checked graph edges, but RWKV responded by
retaining future semantic stages while emitting `dependencies=[]` for all of
them. The validator could see that every structural edge was empty; it could
not determine from Task language that “create,” “verify,” and “read output”
were future stages requiring observations from sibling Tasks.

The result was not observation-driven execution. It was a speculative full
workflow flattened into one dependency-free batch. Parallel action proposal
then asked RWKV to choose producer and verifier actions from isolated pre-read
snapshots. This removed real causal ordering and amplified weak action choices.

This confirms the user's stated warning: adding structural constraints can
become an indirect answer/decision filter and can distort the model's own plan.
The rule is therefore rejected even though its offline graph property passed.

## Case evidence

- `B06`: five Tasks—two reads, create, and two verifies—were all dependency
  free. The create action guessed placeholder prose rather than using the two
  read observations. Agent completion became a false positive.
- `B08`: inspect, compute, write, verify, and read-manifest were all dependency
  free. Several “future” Tasks read the source again; the last Task wrote the
  empty-input SHA256. Production and Agent completion failed.
- `B11`: the same flattened producer/verification pattern completed against an
  externally wrong artifact.
- `B12`: multiple dependency-free reads/writes happened to leave the external
  file correct, but recovery/semantic completion blocked, producing the only
  external pass and a false negative.
- `B18` and `B21`: RWKV failed both allowed plan attempts and no Task was
  materialized.
- `B25`: two source reads and the future merge/verify stages were simultaneous.
  The merge lacked dependency observations and wrote wrong literal filenames.
- `B26`: all five Tasks were flattened. Nominal “read” Tasks selected writes;
  paths and newline content were wrong, while the Agent completed.
- `B27`: both corrected planning attempts remained structurally invalid, so the
  run blocked before mutation. This was safe but not useful capability.
- `B29`: future reads of not-yet-created backup files were made immediately;
  recovery blocked without completing the copy.

## Conclusion

The accepted full Task graph must retain RWKV's dependency decisions. The
Controller must not force those semantic stages into an edge-free shape.
Round49 code and tests are reverted to the Round46 interface.

The next improvement should target a different repeated failure without
rewriting task semantics: weak-model action selection sees all large tool
schemas at once and repeatedly anchors on an incompatible mutating tool for
verification Tasks. A two-stage RWKV-owned protocol—RWKV chooses one tool name
from a compact catalog, then RWKV fills that tool's single schema—can reduce
tool/schema interference while leaving both decisions model-owned. It adds a
request, which is acceptable while correctness is the priority, and must be
audited without Controller-selected names or arguments.
