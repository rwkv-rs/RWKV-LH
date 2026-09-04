# Round50 Preregistered Protocol: RWKV-Owned Progressive Tool Disclosure

## Frozen evidence

The active baseline is the restored Round46 interface: Basic30 Strict `23/30`,
FP `2`, FN `0`, and offline `364/364`.

Cross-round traces show a repeated action-boundary failure that is independent
of wire-format normalization:

- the action prompt exposes all registered tools and all parameter schemas in
  one large G1i dialog;
- `write_file`, the first large schema, is repeatedly selected for Tasks whose
  own postcondition is observation/comparison (`B26`, `B29`);
- `copy_file` is available but `B29` instead reconstructs partial content with
  `write_file`;
- recovery in `B08` keeps the selected read tool but mixes unsupported
  `end_char` with the displayed read schemas;
- Round36 measured 41 `tool + args` wire forms and Round39 found cross-tool
  argument mixing when all 15 schemas were redisplayed during correction.

Round49 demonstrated that Controller-enforced Task reshaping is harmful and is
fully reverted. Round50 does not change planning, dependencies, Task semantics,
Goal evidence, recovery policy, format aliases, or acceptance.

Round46 has a complete Basic30 result but no complete 90-case run under the
uploaded source tree. Before any Round50 source edit, the uploaded commit
`14d864d71bf670b479a33f4fdb63b4772b69d3c8` must therefore run the fixed
RWKV-E2E-90 and be analyzed as `Round46_full90_uploaded_baseline`. This is the
only valid full-suite baseline for the Round50 comparison; Basic30 remains a
diagnostic subgroup and cannot be extrapolated to Medium or Hard.

## One model-boundary change

Split each RWKV action commitment into two RWKV-owned protocol phases:

1. **Tool-name selection.** Present the active execution capsule plus the
   compact registered action catalog. Each catalog entry retains only its
   registered name and description and uses an exact empty-arguments G1i
   selection schema. RWKV must emit one registered tool call with `{}`.
2. Audit the raw selection response, canonical normalized payload, selected
   name, request ID, and catalog digest. The Controller does not choose or
   infer a name.
3. **Argument commitment.** Present the same bounded execution capsule and only
   the full schema of the single tool RWKV selected. RWKV must emit a complete
   G1i call with the same name and all arguments.
4. Validate the second call against that tool's ordinary Harness contract. If
   its arguments are invalid, one correction request retains the same
   RWKV-selected name and the same single schema, as in Round39.
5. The executable `TaskAction` is the complete second RWKV call. No field from
   the first call is copied into the action except as an equality constraint on
   the second RWKV-emitted name.

The additional request is intentionally accepted in this round because
correctness has priority over efficiency.

## Explicit non-cheating boundaries

- Both the selected name and final name/arguments are emitted by RWKV.
- The Controller does not derive a tool from Task title, description,
  postcondition, action result, verifier output, benchmark ID, or expected
  answer.
- The Controller does not rank, reorder dynamically, delete, or hide candidate
  tool names. The choice catalog follows the registered Harness catalog order.
- A tool-choice call with non-empty arguments, unknown name, extra fields, or
  invalid format fails closed; its arguments are never silently discarded.
- The second call may not switch names. A mismatch fails closed rather than
  being rewritten.
- No missing parameter, path, value, content, answer, Task decision, Goal
  decision, or final output is supplied or changed by code.
- Raw and normalized outputs from both phases remain separately auditable.
- The existing format layer retains its only role: registered common wire
  syntax to one canonical representation with semantic values unchanged.
- No external model, verifier, hidden acceptance, answer rule, or service is
  added to the Agent loop.

## Frozen offline validation

- full pytest;
- LH-Control `30/30`;
- E2E catalog `90/90`;
- valid selection and valid argument call produce exactly the second raw
  RWKV action;
- selection catalog contains every registered name once, in stable order, no
  full parameter properties, and unchanged descriptions;
- non-empty selection arguments fail closed without being discarded;
- unknown selection name fails closed;
- second-phase name switch fails closed;
- invalid final arguments retain the selected name and single schema during
  correction;
- raw/normalized payloads and request linkage are complete and recoverable from
  audit/state;
- custom registered actions participate without hard-coded name lists;
- parallel isolated Tasks can perform both phases concurrently;
- the deterministic 31-file architecture regression completes discovery,
  bounded parallel read fan-out, one summary per file, and aggregation with an
  observed parallel frontier of at least two. This fixture validates runtime
  structure only and must not be reported as a real-RWKV large-project pass;
  the frozen `rwkv_lh_large_code_31_v1` real-model task remains a separate
  capability experiment.

## Fixed real canary

Runner canonical order:

`E2E-B06`, `B08`, `B11`, `B12`, `B18`, `B21`, `B25`, `B26`, `B27`, `B29`.

The canary is an early causal check only. Regardless of its score, preserve its
full trace and then run the frozen E2E-90 exactly once for the Round50 candidate;
do not stop at Basic30 or use the canary to avoid a full-suite regression.

Canary diagnostic expectations:

- every materialized action has one preceding audited RWKV tool selection with
  the same name;
- no Controller-selected or Controller-generated tool name/argument event
  exists;
- at least `3/4` of `B06/B08/B11/B18` are Strict;
- at least `2/3` of `B21/B25/B26` are Strict;
- FP among `B12/B27/B29` is at most `1`;
- at least `2/3` of `B12/B27/B29` are Strict or correctly blocked;
- the deterministic 31-file architecture regression passes.

## Retain and upload gate

Retain/upload eligibility is decided on the complete E2E-90 against
`Round46_full90_uploaded_baseline`: Strict must increase, FP must not increase,
FN must not increase, each difficulty group must be reported, offline and the
deterministic 31-file architecture regression must pass, and every raw RWKV
final output must remain byte-exact. Basic30 `23/30` is retained only as a
historical subgroup checkpoint, not the full-suite gate. Request count and
latency are recorded but are not gates in Round50. Dataset, selected set,
canonical runner order, metrics, similarity implementation, sampling, and
thresholds are frozen before code changes.
