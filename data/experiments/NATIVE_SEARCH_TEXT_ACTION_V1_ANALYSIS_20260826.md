# Native `search_text` Action v1 analysis — 2026-08-26

## Outcome

The native backend Action is complete against its preregistered deterministic scope.
All eight frozen cases, pagination union, token bounds, traversal/cursor failures,
binary/encoding/size/symlink exclusions, registry projection, model menu order, and
Controller Action→Observation integration passed. Final full regression:
`287 passed in 57.80s`.

## Systemic fixes discovered during validation

1. Lexical workspace scope is now checked before strict path resolution, so a missing
   `../outside` target is classified as a scope violation rather than a missing file.
2. The search default moved to grep-style regex in a separately preregistered v2 after
   real RWKV repeatedly combined `TODO|FIXME` with literal mode.
3. Direct mode now terminalizes the third identical, successful, idempotent read-only
   zero-progress observation instead of allowing an unbounded success loop.
4. `network_policy` is retained in the bounded model result projection after full-suite
   validation exposed that the security fact existed in ActionResult but was omitted
   from typed decision state.

These changes are global path, loop, and fact-projection rules; none special-cases a
dataset path, marker, or expected locator.

## Model-level boundary

The full-disclosure real RWKV run completed with one successful `search_text` call and
exact locator F1 `1.0`, proving the backend/model execution path. It still failed the
pre-registered semantic priority metric by placing `HIGH` before
`SECURITY CRITICAL`. Therefore the deterministic Action is complete, while the
end-to-end Agent capability remains only partially validated. See
[the backend gap audit](RWKV_LH_AGENT_BACKEND_GAP_AUDIT_20260826.md).
