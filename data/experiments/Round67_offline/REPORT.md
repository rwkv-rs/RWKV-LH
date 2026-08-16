# Round67 offline validation report

## Result

- Complete production/unit/integration collection: `416/416` passed.
- LH-Control deterministic architecture regression: `30/30` passed.
- Frozen E2E catalogs/reference plus the 31-file parallel summarize/read
  architecture regression: `5/5` passed.
- Python compilation and `git diff --check`: passed.

The complete pytest collection was executed in disjoint, exhaustive file groups:

- `tests/test_long_horizon_controller.py`: `113/113`.
- `tests/test_tool_protocol.py`: `82/82`.
- All other test files: `221/221`.

The `5/5` frozen subset repeats the core30, LH12 and extension48 catalog checks,
the frozen 90-case Codex reference digest check, and the observation-driven
31-file fan-out/summary/aggregation architecture regression. These tests are
already included in the complete `416/416` count and are reported separately as
the preregistered quality gate.

## Round67-specific coverage

- Goal proposals reject unknown fields and semantic type coercion, including a
  string in place of the boolean `required` field.
- Every Goal-obligation capsule retains the exact original request, objective,
  constraints, complete success criteria and Goal digest under projection.
- Goal-obligation recovery and verified-failure recovery share one fixed G1i
  `propose_task_batch` transport.
- Exact bare `{tasks:[...]}` is accepted only at that fixed-tool boundary and is
  audited before and after normalization without modifying any Task field.
- Both recovery paths reject batches wider than four Tasks.
- A top-level `execution_capsule` is accepted only as an object-valued closed
  decoration, separated without interpreting its content, and otherwise rejected.

## Dataset record

- Source: repository test suite and frozen benchmark catalogs at the Round67
  working tree.
- Version: `Round67`, preregistered in
  `data/experiments/Round67_PROTOCOL.md` before live model execution.
- Purpose: verify protocol integrity, immutable Goal recovery, non-intervention,
  and architecture regressions before the fixed15 live RWKV canary.
- Generation: exhaustive pytest file groups plus
  `scripts/run_lh_control_benchmark.py --output
  data/experiments/Round67_offline/lh_control_30`.
- Detailed LH-Control outputs and per-case SQLite/audit records are stored under
  `lh_control_30/`.
