# Round46 Upload Fix Protocol: Deterministic Python Runtime Alias

## Trigger evidence

The pre-upload full regression executed with a repository-owned `TMPDIR` and
finished with `363 passed, 1 failed`. The only failure was
`test_command_interface_resolves_python_alias_inside_the_same_sandbox`.
`check_command(["python", ...])` executed successfully, but recorded
`resolved_argv[0]="python"` instead of the active RWKV-LH Python runtime.

The cause is environment-dependent code in `ActionHarness._run_command`:
`python` is resolved to `sys.executable` only when `shutil.which("python")` is
absent. Under `uv run`, the virtual environment adds a `python` executable to
PATH, so the same canonical model action changes resolution behavior according
to launcher environment.

## Frozen change

- When and only when the first argv token is exactly the registered canonical
  alias `python`, resolve it unconditionally to
  `Path(sys.executable).resolve(strict=True)`.
- Preserve the original RWKV-emitted argv separately in metadata.
- Do not rewrite any other executable, argument, command output, tool choice,
  semantic decision, or final answer.
- Keep `shell=False`, workspace scope, bubblewrap mapping, timeout, and
  environment handling unchanged.

## Frozen validation

1. The existing failing test must pass without changing its expectation.
2. Full pytest must pass.
3. LH-Control must remain `30/30`.
4. E2E catalog validation must remain `90/90`.
5. The current source tree must differ from the Round46 E2E manifest only in
   this preregistered generic command-interface fix and documentation/tests or
   experiment records; no rejected Round47--49 scheduler code may reappear.

This upload fix is an execution-interface determinism correction. It is not a
new model-quality round and does not authorize attributing the existing
Round46 Basic30 score to a newly run model experiment.
