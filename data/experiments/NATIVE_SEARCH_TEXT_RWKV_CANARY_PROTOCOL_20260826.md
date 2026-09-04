# Native `search_text` RWKV canary protocol — 2026-08-26

## Purpose

Verify that the configured RWKV model can autonomously select the newly registered
`search_text` backend action, consume its observation, and report the complete frozen
TODO/FIXME set without modifying the workspace.

## Frozen workspace and request

Workspace: `data/experiments/NATIVE_SEARCH_TEXT_RWKV_CANARY_20260826/workspace`

Request (verbatim):

> 搜索当前项目中的 TODO 和 FIXME，按紧急程度排序，列出每一项的文件路径、行号和理由。不要修改任何文件。

Frozen matches, ordered by the explicit severity words in their source lines:

1. `src/api.py:2` — `TODO SECURITY CRITICAL: prevent production auth bypass`
2. `src/cache.py:2` — `FIXME HIGH: eliminate cache race before release`
3. `docs/notes.md:1` — `TODO LOW: improve optional examples`

## Pre-registered metrics and thresholds

- Run status must be `completed`.
- The committed action sequence must include at least one successful `search_text`.
- Workspace mutation action count must equal zero.
- Locator-set precision, recall, and F1 use exact `(relative_path, one-based line)`
  equality and must all equal `1.0`.
- Highest-priority exactness is binary: the first ranked locator must be
  `src/api.py:2`; threshold `1.0`.

No metric, expected locator, severity ordering, or threshold may be changed after
the first model request is sent.
