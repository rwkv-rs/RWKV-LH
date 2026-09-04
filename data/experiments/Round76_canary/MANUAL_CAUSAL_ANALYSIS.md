# Round76 short7 manual causal analysis

## Frozen result

- Strict `0/7`; External `0/7`; Agent completed `0/7`; FP `0`; FN `0`.
- All seven runs blocked during the first Task step. No Harness action executed.
- The preregistered gate failed. No fixed15 or full90 run was started.

The conclusions below come from each case's first raw Task-step output and contract errors, not from aggregate scoring.

## Per-case first wrong transition

- **B01:** RWKV correctly chose `act` but copied `long-horizon.task-action-ledger.v1` from the displayed causal-state object into the response schema. Its concrete action was also semantically wrong (`read_file` on `.` instead of directory listing). All three retries retained the wrong response schema.
- **B02:** RWKV returned `complete` before reading anything and invented `T1-input.txt` as evidence. The controller correctly rejected the unknown ref; retries repeated it, then returned completion with no refs.
- **B10:** RWKV treated existence of `test_slug.py` as if its contents had been read and invented ref `T1`. Three unknown-ref rejections blocked the run.
- **M01:** RWKV claimed three service files had already been read and invented refs `T1-1`, `T1-2`, `T1-3`. No observation existed.
- **M03:** RWKV copied the causal-ledger schema and claimed file existence directly established source inspection, citing invented ref `T1`.
- **M06:** RWKV copied the causal-ledger schema and entered a long repetition claiming the Goal was already satisfied from `selection.txt` existence. No copy/read observation existed.
- **M12:** RWKV treated `math_utils.py` path existence as source-content observation and invented the path string itself as an evidence ref.

## Shared cause

The single complete-action structure is simpler internally, but its initial request still offers `complete` when the evidence registry is empty. The prompt therefore asks a weak model to choose an impossible lifecycle branch, then relies on a later unknown-ref validator to reject it. Four cases take that branch immediately. Three other cases copy the nearby causal-state schema because the input contains two competing `schema_version` values.

This is not evidence that the controller should accept invented refs or file existence as content. The strict rejection prevented false positives. The next correction is structural feasibility, not answer correction:

1. If the displayed evidence registry is empty, the only feasible decision is `act`; the controller still does not choose the action or arguments.
2. Remove presentation-only `schema_version` from the Task-local causal ledger so the output contract is the only schema version in the request.
3. Keep `complete` available whenever real dependency/current refs exist, preserving M01's valid dependency-evidence completion path.
4. Do not alias the old ledger schema to the new Task-step schema; the converter must not hide the collision.

Round76 therefore rejects the full-action design as currently prompted, but not yet the one-transition architecture itself. The seven failures occur before any action and are explained by the same two prompt/protocol defects.
