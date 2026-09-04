# `search_text` regex-default v2 protocol — 2026-08-26

## Root cause under test

The frozen v1 RWKV canary used `pattern="TODO|FIXME"` with `mode="literal"`,
obtained a complete zero-match result, and repeated the exact successful action 67
times. The tool description already mentioned regex alternatives, so adding a
case-specific prompt is not an acceptable fix.

## Single variable

Change only the model-facing and executable default search syntax from `literal` to
`regex`. Keep explicit `mode="literal"` behavior unchanged. This matches the usual
grep-style meaning of a search pattern and makes alternation work without semantic
argument inference by the controller.

## Frozen checks and thresholds

- All v1 frozen dataset cases retain exact expected locator equality because every
  dataset case declares its mode explicitly.
- Add exact default-mode coverage: omitted `mode` with `TODO|FIXME` must return the
  union of both markers in deterministic locator order.
- All targeted and full regression tests must pass.
- Repeat the unchanged RWKV canary request and workspace under a new run id.
- Canary thresholds remain those in
  `NATIVE_SEARCH_TEXT_RWKV_CANARY_PROTOCOL_20260826.md`; no expected locator or
  ranking threshold changes are permitted.
