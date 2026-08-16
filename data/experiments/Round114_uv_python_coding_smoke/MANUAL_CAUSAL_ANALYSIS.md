# Round114 manual causal analysis

## Result

- Strict: `0/2`
- Agent completed: `1/2`
- External hidden acceptance: `1/2`
- Final: `2/2` non-empty and byte-for-byte derived from raw RWKV output

This round did not establish the uv runtime fix in the real benchmark because a
benchmark harness override still implemented the former sandbox method signature.
It did establish two different downstream amplification chains.

## E2E-B10 — Agent completed, external failure (FP)

1. RWKV planned one Task whose `done_when` required passing `test_slug.py`, but
   declared `file_content_read` on `slug.py` instead of command evidence.
2. RWKV read `slug.py` and wrote an implementation. The implementation replaced
   each literal space independently, so it did not collapse an internal run of
   spaces and was semantically wrong for `test_spacing`.
3. RWKV correctly selected `python -m pytest test_slug.py` with expected exit code
   zero. Before a process was started, `FaultInjectingHarness._bubblewrap_command`
   raised `TypeError` because its old override did not accept
   `include_project_venv`.
4. The unchanged-failure guard rejected the same retry. After one wire rejection,
   RWKV fell back to reading the written file.
5. Because the Task's original evidence contract was only `file_content_read`, the
   successful read made the structural completion gate ready. RWKV then committed
   `lh_task_done` without a successful test observation and completed the Goal.

Root chain: weak Goal evidence contract + stale subclass interface -> correct test
decision never executes -> recovery falls back to file observation -> structural
gate permits RWKV's false completion decision. The wrong algorithm value itself was
produced by RWKV and was not changed by the controller.

## E2E-B30 — external success, Agent blocked (FN)

1. RWKV wrote a correct `normalize_name` implementation; hidden unittest later
   passed and `NotImplementedError` was absent.
2. The controller correctly rejected immediate `lh_task_done` because the Task
   explicitly required command evidence for `python test_names.py`.
3. RWKV then selected the correct command twice, but included the read-operation
   field `max_tokens`. The strict command action schema rejected both calls before
   execution as an unknown argument.
4. RWKV degraded to repeating the already-successful `write_file`; the unchanged
   action guard rejected three repeats. Goal replanning then repeated an isomorphic
   Task and was suppressed as no progress.
5. The run blocked even though the workspace was correct. The Final text also
   contradicted the artifact by claiming the implementation still lacked whitespace
   joining.

Root chain: correct RWKV code value -> correct completion gate requests a test ->
minor command-interface friction wastes the correct test decision -> recovery
degrades to unchanged writes and no-progress replans -> FN. This is separate from
the uv mount itself because neither rejected command reached the harness.

## Corrective action and rerun boundary

- Forward the complete base `_bubblewrap_command` keyword interface from
  `FaultInjectingHarness`, retaining the benchmark's network isolation.
- Add a benchmark-harness regression that runs `python -m pytest --version` inside
  bubblewrap using the current project uv environment.
- Do not alter either model-generated implementation or hidden acceptance.
- Rerun the same two frozen cases as Round115. Round115 may still expose the
  independent B30 `max_tokens` interface issue; that outcome must be reported rather
  than hidden by changing the frozen run.
