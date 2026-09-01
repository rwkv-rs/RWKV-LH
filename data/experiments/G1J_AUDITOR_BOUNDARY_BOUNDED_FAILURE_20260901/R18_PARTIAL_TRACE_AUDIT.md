# R18 partial trace audit

Date: 2026-09-02. R18 is infrastructure-invalid as a scored run: the first
uncached StageReview after eight RWKV actions failed twice with HTTP 429. The
direct evidence is `results.json.results[0].supervisor_failure` with
`phase=goal_stage_review`, `http_status=429`, and the final two causal records
`strong_stage_checker_call_failed` / `run_yielded`. This downstream stop is not
an RWKV failure.

The valid prefix still exposes role-specific capability defects:

- Selector/Executor action `A00003`, repeated as `A00004` and `A00007`, ran
  `python -m unittest discover -s tests -p test_*.py`, although the observed
  workspace contained `verify_project.py` and no `tests/` directory. The first
  wrong operation boundary is the `exact_tool_selection_staged` record before
  `A00003`; the Executor independently supplied the wrong argv.
- Executor actions `A00005` and `A00006` created runnable Python, but direct
  execution of the immutable verifier fails at `verify_project.py:41` because
  `add_note` returns a string rather than the required note object. The same
  output also returns a dictionary rather than a boolean from `remove_note`,
  omits the global `--db` CLI option, handles only one `--tag`, and does not
  print the required JSON objects.
- Auditor request for `A00003` first emitted `params` without `step_id`; the
  request for `A00004` required three attempts; the request after `A00006`
  twice claimed completion despite the missing `README.md`, then omitted the
  exact six-field schema. The Controller correctly rejected these records and
  did not grant completion authority.
- The cached Stage 1 review incorrectly demanded implementation and verifier
  success that belonged to future stages. Its linked Planner patch only added
  Stage 4, leaving the existing Stage 2 frontier unchanged. This identified a
  structural repair bug rather than an RWKV training target.

The structural findings were fixed generically: rejected PlanPatch candidates
are validated on an isolated plan; StageReview repair must change current
frontier work; Stage Checker instructions exclude future-stage obligations;
and its facts are restricted to accepted evidence from the reviewed stage.
R18 infrastructure records and the StageReview-induced trajectory are excluded
from State Tune datasets. Only exact RWKV role boundaries with valid upstream
inputs may be retained as correction candidates.
