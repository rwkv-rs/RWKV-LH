# Round115 manual causal analysis

## Frozen result

- Strict: `1/2`
- Agent completed: `1/2`
- External hidden acceptance: `1/2`
- Final: `2/2` non-empty and raw-RWKV matching
- Offline regression before run: `112/112`; unified control: `74/74`
- Runtime: uv `0.12.5`, Python `3.13.11`, pytest `9.1.1`

## What the round proves

The uv Python environment defect is fixed across the real benchmark boundary, not
only in a unit fixture. Model-selected commands ran inside bubblewrap with
`executable_resolution=python_alias_to_project_runtime`. B10 imported pytest 9.1.1
from the project uv environment, and B30 executed the workspace unittest. The
workspace was writable while the uv environment was mounted read-only.

## E2E-B30 — strict PASS

1. RWKV created `names.py` with a correct regex-based normalization algorithm.
2. RWKV prematurely selected `lh_task_done`; the controller rejected it because the
   RWKV-authored Task contract required command evidence. This gate did not decide
   whether the code was correct; it required the model to obtain its own declared
   observation.
3. RWKV selected `check_command` with `python test_names.py`.
4. The command ran inside bubblewrap through the uv Python runtime and returned exit
   code zero with one passing unittest.
5. RWKV committed task and Goal completion and produced a matching non-empty Final.
6. The independent hidden verifier also passed its unittest and confirmed that
   `NotImplementedError` was absent.

This is a complete concrete example of the current Agent creating a file, replacing
an unimplemented algorithm with model-generated code, executing it, observing the
test result, and closing the task without controller-generated business values.

## E2E-B10 — blocked, external FAIL

1. RWKV read the stub and wrote a `slugify` implementation using literal
   `value.replace(" ", "-")`.
2. `python -m pytest test_slug.py` successfully ran through the uv environment. Its
   exact observation reported `pytest-9.1.1`, two collected tests, one pass and one
   failure: `multiple---spaces` versus `multiple-spaces`.
3. RWKV received this concrete failure repeatedly but rewrote the same semantic
   implementation and reran the same failing test. After the first supersede it also
   read `test_slug.py`, then repeated the same algorithm under unittest.
4. A second supersede again exposed both code and test. RWKV eventually removed one
   no-op line but retained literal one-space replacement, so the failure remained.
5. Repeated unchanged writes exhausted recovery and the Goal lane proposed only
   isomorphic replacements, which the no-progress gate suppressed. The run blocked.
6. Final text still incorrectly claimed literal replacement collapses a whitespace
   run, contradicting the visible test failure.

The earliest causal error is RWKV's algorithm choice. The environment, command
transport, failure observation, and external verifier all behaved correctly. The
architecture still amplifies the error by allowing many same-semantic rewrites and
isomorphic recovery cycles (`41` model requests, `25` attempts, `2` replacements)
instead of giving RWKV one compact comparison between the failed actual value and
expected value and demanding a materially changed producer action.

## Remaining boundary

The current system can complete a simple coding task, but the result is not yet
reliable across simple tasks. The next quality fix should target same-semantic
producer correction after a precise test assertion—not Python packaging, and not a
controller-side rewrite of the algorithm. B30 from Round114 also remains evidence
that an unsupported observation annotation such as command `max_tokens` can waste a
correct model decision; that interface issue should be handled independently by the
small format-conversion boundary.
