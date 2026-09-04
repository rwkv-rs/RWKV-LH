# EXE-G6 dev evaluator metadata completeness addendum

Frozen on 2026-08-29 before any G6 checkpoint evaluation.

The frozen evaluator requires a declared `language` field although the field is
not consumed by the model and is absent from 384 of the 480 frozen G6 dev rows.
Create one evaluation-only projection that adds `language=zh` when the existing
prompt contains a CJK character and `language=en` otherwise. Preserve line
order and every existing field byte-for-byte; in particular, prompt, target,
sample ID, selected operation, source kind and source-family identity cannot
change. The state-tuning files, training manifest and model inputs remain
untouched. This projection is metadata-only and may not inspect any RWKV output.
