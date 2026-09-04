# Goal UI remote dual-GPU product preview

Date: 2026-08-30 (Asia/Shanghai)

## Purpose and scope

This record covers an isolated product-preview deployment for the Goal web UI.
It is not a formal architecture ablation or a benchmark run. No checkpoint,
training job, optimization job, registered evaluation threshold, or existing
product service was changed. No Goal task was submitted during deployment
validation.

## Topology

- Local WSL: Goal web UI, Controller/Harness, append-only run data, and SSH
  tunnels.
- Strong Planner/Reviewer: `gpt-5.4-mini`, `contract_graph`, reasoning `none`.
- Remote physical GPU1: Executor served as
  `rwkv7-g1i-13.3b-exe-g3-g6-deterministic-cmix-r7-multiprofile-ctx2496`.
  Default offline profile is `EXE-G3-MULTISTAGE-STEP2000`; the network recovery
  profile remains available to the multi-profile service.
- Remote physical GPU2: exact-tool Selector `rwkv7-g1i-2.9b-vllm-v1`, S60
  head SHA-256 `721669ce8733b590b3aa6c910d8bc13d744612f1fee884d5276a3f0d96d0d441`,
  v7 requirement-byte-tail input protocol, and zero initial-state profile.
- Existing remote GPU0 service and GPU3 workloads were left running and were
  not reconfigured.

## Endpoints and service isolation

- Goal UI: `127.0.0.1:8766`, data root `data/goal_ui_preview/`.
- Local Executor tunnel: `127.0.0.1:29613` to remote `127.0.0.1:18075`.
- Local Selector tunnel: `127.0.0.1:29621` to remote `127.0.0.1:18076`.
- Remote transient units:
  `rwkv-lh-goal-ui-g3g6-gpu1.service` and
  `rwkv-lh-goal-ui-s60-gpu2.service`.
- Local transient units:
  `rwkv-lh-goal-ui-selector-tunnel.service` and
  `rwkv-lh-goal-ui-web.service`.

The pre-existing web UI on port 8765 and its run data were not modified.

## Validation

- `uv run pytest -s -q tests/test_web_ui.py`: 11 passed.
- JavaScript syntax, Python bytecode compilation, and `git diff --check` passed.
- `/api/runtime/topology` reported the Supervisor configured, Executor
  available with the exact served model, and Selector available with exact
  runtime identity equality.
- `/api/runtime/health`, `/api/runs`, the HTML shell, and the JavaScript asset
  returned successfully over port 8766.
- Remote GPU inventory after startup showed the preview services on physical
  GPU1 and GPU2. Existing compute processes remained on GPU0 and GPU3.

The first Selector start correctly failed closed because the profile manifest's
referenced tensor was absent on the remote host. The complete registered profile
directory was then copied; the service subsequently loaded and returned the
expected runtime identity. No fallback identity was accepted.

## Interpretation boundary

This deployment proves service wiring, identity pinning, UI/API availability,
and isolation only. It does not improve or supersede the latest registered
end-to-end quality result. Real Goal submissions should be treated as product
tests and judged from their complete plan, action, evidence, file, and audit
records rather than from a success badge alone.
