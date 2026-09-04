# Current Architecture Cleanup V1

## Registration

- Date: 2026-09-04 (Asia/Shanghai)
- Source revision: branch `chase/rwkv-goal-loop-v2-cleanup`, working tree after `e4ef2de7858f91d728dc56d9661767ac6a170dc6`
- Purpose: remove code, dataset stubs, tests, generated output, and documentation that are not part of the current `rwkv-stateful-goal-loop.v3` chain
- Scope: repository closure, role input/output contracts, Selector identity, native-state runtime health, and E2E catalog validity
- StateTune: not run and not modified

## Method

1. Remove visible untracked files with `git clean -fd`.
2. Remove ignored local artifacts, including `temp/`, environments, model copies, runtime state, logs, outputs, caches, and per-case workspaces, with scoped `git clean` operations.
3. Remove tracked scripts and tests whose only inputs were absent, untracked datasets or discarded experiment paths.
4. Keep the current G1J role dataset generators, Selector Head pipeline, inference stack, long-horizon runner, web UI, smoke tests, and RWKV-E2E runner.
5. Rewrite `README.md` and `docs/HANDOFF.zh-CN.md` against current source contracts.

## Evidence

- Initial clean-checkout test: `65 failed, 578 passed`; all failures referenced absent untracked datasets or an absent untracked adapter.
- After closure cleanup: `559 passed in 46.41s`.
- `uv run rwkv-lh-runtime-smoke`: 13.3B endpoint healthy at `http://127.0.0.1:29613/v1`.
- Native recurrent-state capability: create, resume, fork, commit, rollback, export, and import all declared available.
- `uv run rwkv-lh-e2e --suite all --validate-only`: `RWKV-E2E-90`, 90/90 catalog entries valid.
- `git diff --check`: passed.

## Current unresolved boundary

The Selector endpoint was reachable before local runtime artifacts were removed, but its served Head identity did not match the configured release identity. Expected file SHA began `49538a32`; served file SHA began `71d69959`. The product therefore failed closed. This is a deployment identity mismatch, not a missing tool or a second architecture.

The current Head also selects `ABSTAIN` incorrectly on real Chinese multi-tool frontiers. Existing evidence does not distinguish base-model capacity from Head/input-distribution quality, so no claim about the 2.9B base model is registered here. That question requires a fixed zero-State/StateTune holdout ablation.

## Result

The tracked project is self-contained under the current architecture contracts, the clean test suite passes, and no StateTune result has been introduced. Remaining model and deployment defects are listed in `docs/HANDOFF.zh-CN.md` and are not marked resolved.
