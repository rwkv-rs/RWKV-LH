# Round66 offline validation report

## Result

- Production/unit/integration regression: `408/408` passed.
- LH-Control deterministic architecture regression: `30/30` passed.
- Frozen catalog/reference and 31-file parallel summarize/read architecture regression: `4/4` passed.
- Python compilation and `git diff --check`: passed.

The execution channel terminates a single command at approximately 30 seconds, so the
same full pytest collection was executed in disjoint file/keyword groups. Collection
contained 408 tests; the passing groups were:

- `tests/test_long_horizon_controller.py`: `63 + 44 = 107/107`.
- criterion/runtime/state/tool-protocol group: `230/230`.
- snapshot/witness/E2E-catalog/web/runtime-compat/analysis group: `71/71`.

No test was deselected from the combined result. The process-tree timeout regression
was also run independently and passed `1/1`; it is already included in the 230-test
group.

## Round66-specific coverage

- `read_files` reads only the exact RWKV-selected path list, returns per-file content,
  digest and completeness, and rejects duplicate, escaping, or invalid bounded inputs.
- `patch_json` preserves every unspecified top-level field and replaces only explicit
  RWKV-provided keys.
- Compact Task ledgers retain every attempted action's exact path list.
- Identical workspace revisions are represented once in the model-facing evidence
  view while all raw refs and the oldest-to-newest revision chain remain named.
- Goal-obligation recovery is a single G1i `propose_task_batch` call whose semantic
  payload is only the five-field Task array.
- Common observed decorations and fixed write controls normalize only at the model
  boundary; type conflicts and ambiguous forms remain rejected.

## Dataset record

- Source: repository test suite and frozen benchmark catalogs at the Round66 working
  tree.
- Version: `Round66`, preregistered by `data/experiments/Round66_PROTOCOL.md` before
  the model canary.
- Purpose: verify structural integrity and non-intervention before live RWKV runs.
- Generation: pytest commands plus
  `scripts/run_lh_control_benchmark.py --output data/experiments/Round66_offline/lh_control_30`.
- Detailed LH-Control outputs and per-case state are stored under `lh_control_30/`.
