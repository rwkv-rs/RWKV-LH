# Round45 Canary Causal Analysis

## Frozen result

- Strict: `7/10`.
- External: `7/10`.
- Agent completed: `9/10`.
- Strict passes: `B06`, `B08`, `B11`, `B18`, `B21`, `B25`, `B26`.
- Both failed and correctly blocked: `B04`.
- False positives: `B27`, `B29`.

Round45 passed the positive-control gate (`4/4`) and the historical verification-chain gate (`3/3`) but exceeded the fixed FP limit (`2 > 1`). No Basic30 run is permitted and Round45 alone is not eligible for upload.

## Confirmed benefit

The compact ownership instruction made RWKV treat complete read/list evidence as the material it must itself verify. All three historical observation/verification failures (`B21`, `B25`, `B26`) completed correctly, and all four correct controls remained Strict. This is much better than Round44's extra JSON observation schema, which produced only `4/10` Strict and leaked view metadata into tool calls.

## B27 exact failure chain

1. Producer `replace_text` changed only one of three occurrences.
2. Verification Task `T3` read the complete wrong file.
3. On its first Task-commit response, RWKV correctly reasoned that `protocol=v1` remained and emitted `decision=replan` after the reason.
4. That response omitted only `schema_version`; its semantic fields were otherwise exactly the requested `reason` and `decision`.
5. The current schema converter deliberately leaves a missing schema unchanged. Canonical validation rejected the response and requested a second model sample.
6. The second sample changed the semantic decision to `pass` and falsely stated no occurrence remained.
7. Goal adjudication then passed all criteria, and the final answer simultaneously displayed the remaining v1 lines while claiming success.

The first correct RWKV decision was not honored because a pure format omission forced semantic resampling.

## B29 exact failure chain

The producer wrote only the final source line to `backup/source.txt`, so the workspace was wrong. Task and Goal decisions then claimed equality despite different artifact hashes/content. Unlike B27, this is a remaining RWKV semantic comparison error; accepting missing schema alone cannot be assumed to fix it.

## Architectural conclusion

Round45 exposed a format-boundary defect that directly matches the project's intended converter scope. A Task-commit object with exactly `reason` and `decision` but no `schema_version` is a common wire form observed repeatedly in this fixed run. Adding the one fixed canonical schema tag is representation normalization: it preserves every emitted semantic field and value and prevents a second sample from replacing RWKV's decision.

The next round must preregister the integrated boundary explicitly:

- retain the compact RWKV-owned Task verification instruction;
- register only the exact two-field Task-commit omission form;
- insert only the fixed canonical schema tag;
- reject missing-schema objects with any other field set;
- retain raw and normalized payloads/digests;
- never parse reason or alter decision;
- add no Goal rule, verifier, or external acceptance path.

Round45 prompt code is reverted before Round46 and Round45 is not uploaded.
