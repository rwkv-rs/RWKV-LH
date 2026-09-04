# Round116 v15-A Atomic Causal Task Spine preregistration

Date: 2026-08-15

Status: frozen design before runtime implementation. Source hashes must be appended after
implementation and before the first online run. Results may not change this protocol.

## One architecture variable

Round116 changes one indivisible Task lifecycle boundary:

```text
local Task revision
  -> one complete registered Action
  -> exact Harness Observation and artifact revision
  -> RWKV decision-last complete or repair
```

The online Task proposal contains only `key`, `objective`, `done_when`, and `after`.
`evidence_kind` and `evidence_subject` are not generated at plan time and are not completion
contracts. A normal Task revision may record at most one successful Harness Action. A failed
or protocol-rejected call remains visible; fixed transient retry policy is not changed by this
round. After a successful Action the Task lane cannot execute another independent Action:
RWKV must commit the revision or return to the Goal lane for a successor/replacement Task.

The successful ActionResult, Observation and artifact revision survive repair/supersede.
Later mutation invalidates reuse of evidence tied to the old artifact revision. Controller does
not infer business roles, expected values, tools, members or answers from Task text.

## Explicitly excluded

- no reviewer, judge, selector, frontier role or new completion gate;
- no no-progress fingerprint or recovery-budget redesign (reserved for separately registered
  v15.1 if v15-A passes Basic30);
- no workset/member-ledger behavior change in Round116;
- no native-state claim while transport remains `prompt_replay`;
- no semantic rewriting of RWKV Action arguments, Final text or business outputs.

## Frozen data and runtime

- Official capability set: frozen RWKV-E2E-90 catalogs registered by
  `data/datasets/rwkv_e2e_90_v1/manifest.json`; dataset hashes must remain equal to that
  manifest. The four historical core/LH copies in `data/datasets/rwkv_lh_e2e_v1/` remain
  byte-identical to their catalog sources.
- Historical LH-Control: `lh-control-30.v1`, SHA256
  `0606877c66360aefbf243b848a19fb349927e7a32e86565dbdc58e41ddcfbe80`.
- Current-contract LH-Control: `lh-control-30.v2`, SHA256
  `3a98077f3cc19e4ecd8b9fe2119aef65a6502eabdc3f123f876d886355a118d6`.
  Results from v1 and v2 are reported separately.
- Model: `rwkv7-g1i-13.3b-20260805-ctx16384` through the configured local endpoint.
- Sampling: temperature `0.05`, top-p `1.0`, top-k `0`; existing penalties unchanged.
- Basic30: `max-transitions=200`, case concurrency `1`.
- Environment: WSL `UbuntuRecovered`, `/home/chase/.local/bin/uv 0.12.5`, frozen project
  environment and existing bubblewrap policy.

## Required offline checks before online execution

1. All current offline tests pass.
2. E2E-90 catalog validation is `90/90`.
3. Task proposal rejects missing `key/objective/done_when/after` but neither accepts nor
   requires plan-time evidence fields.
4. A normal Task revision cannot execute a second successful Action.
5. Failed Action and fixed transient retry behavior do not consume the one-success boundary.
6. A successful Observation can be followed only by RWKV complete or Goal-level repair.
7. Repair preserves exact ActionResult/artifact refs; later artifact revision cannot reuse stale
   completion evidence.
8. Raw Final remains non-empty at terminal state and byte-identical to RWKV output.

## Stage A: fixed Basic30

The official run contains exactly `E2E-B01` through `E2E-B30`; no single-case optimization is
performed first.

Acceptance requires all of:

- Strict `>=24/30`;
- FP `<=1`, FN `<=1`;
- retain at least `23/24` Round46 Basic true positives;
- artifact UTF-8 byte-5gram cosine mean `>=0.984508565952`;
- B05/B10/B12 are not blocked by redundant downstream Task work;
- B15/B19/B20/B26 are not blocked by plan-time evidence contracts;
- a later mutation cannot reuse pre-mutation completion evidence;
- every case receives manual earliest-divergence and downstream-amplification review.

Missing expected artifacts have similarity `0`. The report records Strict, External, Agent,
FP, FN, requests, Tasks, Attempts, prompt tokens, artifact similarity, Final presence and raw
equality. Request/token reduction is diagnostic, not an acceptance substitute.

## Official and confirmatory runs

Run one official Basic30. If it passes, run one confirmatory Basic30 with identical source,
data, parameters and case order. Report both; never select the better result. A run may be
invalidated only by an auditable endpoint disconnect, service restart, runner crash outside the
case, or corrupted result store. Protocol errors, timeouts, blocked runs and wrong answers are
valid model/architecture outcomes.

Both runs must satisfy Strict/FP/FN and retained-TP gates before Stage B. Similarity and detailed
per-case differences are reported for both; any threshold miss stops promotion pending causal
analysis, without adding a local rule to Round116.

## Commands

The source manifest and exact output directories are appended before execution. Command shape:

```bash
/home/chase/.local/bin/uv run python /home/chase/GitHub/RWKV-LH/scripts/run_rwkv_e2e_benchmark.py \
  --suite all \
  --case E2E-B01 --case E2E-B02 --case E2E-B03 --case E2E-B04 --case E2E-B05 \
  --case E2E-B06 --case E2E-B07 --case E2E-B08 --case E2E-B09 --case E2E-B10 \
  --case E2E-B11 --case E2E-B12 --case E2E-B13 --case E2E-B14 --case E2E-B15 \
  --case E2E-B16 --case E2E-B17 --case E2E-B18 --case E2E-B19 --case E2E-B20 \
  --case E2E-B21 --case E2E-B22 --case E2E-B23 --case E2E-B24 --case E2E-B25 \
  --case E2E-B26 --case E2E-B27 --case E2E-B28 --case E2E-B29 --case E2E-B30 \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/Round116_v15a_basic30_official \
  --max-transitions 200 --concurrency 1
```

Confirmatory output, if eligible:
`data/experiments/Round116_v15a_basic30_confirmatory`.

## Promotion and stop rule

Stage B collection cases and complete E2E-90 remain exactly those registered in the full-history
audit. They are not run unless both Basic30 gates pass. Complete E2E-90 must exceed Round46
Strict `31/90` while FP `<=24`, FN `<=1`, Basic `>=24`, Medium `>5`, and Hard `>2`.
Otherwise v15-A is rejected or revised as a new preregistered experiment; reviewer/gate patches
are not stacked onto the failed source.

## Source freeze (append before first online run)

Frozen at `2026-08-15T09:15:12Z` on branch `chase/g1i-tool-protocol`, Git HEAD and remote base
`14d864d71bf670b479a33f4fdb63b4772b69d3c8`. Because the architecture from Round47 onward is
an intentionally uncommitted historical working tree, the authoritative freeze is the direct
file hash manifest at `data/experiments/Round116_v15a_source_manifest.json`, not the branch name
alone.

- Runtime/test ordered bundle SHA256:
  `f7404dc869ebcfc80fdd78e791ff85b67fa7ea768d4b7236ebf4ee29b68947f6`.
- Tracked binary diff SHA256:
  `640dfe76d76c471b7e6f9af4f726fe0c4a6de6921253cfa434c80156fd2df1eb`.
- Full porcelain status SHA256 (including untracked paths):
  `782d9ec979415a948df814603f1461393e4d90cc347493e32c8bb9943defca97`.
- Offline result: `112 passed in 23.59s`; unified-control result:
  `74 passed in 17.64s`; E2E catalog: `90/90`, `catalog_valid=true`; compileall and
  `git diff --check` passed.
- Endpoint was reachable immediately before the freeze and returned model
  `rwkv7-g1i-13.3b-20260805-ctx16384`, owner `vllm`, maximum context `16384`.
- Runtime environment: WSL2 kernel `6.18.33.1-microsoft-standard-WSL2`,
  `/home/chase/.local/bin/uv 0.12.5`.

The source manifest contains every individual source, test, catalog and LH-Control hash. No
runtime source or test file may change between this freeze and the official/confirmatory runs.
