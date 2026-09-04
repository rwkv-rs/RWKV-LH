# RWKV-LH Exact-Tool Selector v1

This directory is a candidate pool, not a frozen training dataset.

- Labels come only from successful RWKV-authority Harness actions in fully
  accepted runs or byte-exact accepted final boundaries. Atom-graph and
  pre-ensemble direct-action records use separate fail-closed source adapters.
- Direct-action rows require an exact raw-generation/request/decision/action
  join and are rejected if order ensemble or controller semantic synthesis was
  used.
- Raw RWKV output is retained with its UTF-8 SHA-256 and is never rewritten.
- The 20-class input contains tool names/descriptions, never parameter schemas.
- `coverage.json` is authoritative. Training is forbidden while
  `eligible_to_freeze=false`; in that state no train/dev/test files are emitted.
- Duplicate filtering is class-conditional. Cross-label near neighbors are
  retained because they represent causal state boundaries.

Build the candidate inventory:

```text
python /home/chase/GitHub/RWKV-LH/scripts/build_exact_tool_selector_dataset_v1.py
```

`--freeze` fails closed until every class has at least 30 test rows.
