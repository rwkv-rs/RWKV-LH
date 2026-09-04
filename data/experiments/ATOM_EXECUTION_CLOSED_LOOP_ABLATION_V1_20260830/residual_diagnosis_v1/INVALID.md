# Invalid analysis marker

This directory is invalid and must not be used for any conclusion, threshold,
training decision, or comparison.

Reason: `DIAGNOSIS.json` encoded an unbounded single-eligible-label margin as
the non-standard JSON token `Infinity`.  Although Python accepted the file, it
is not strict interoperable JSON and violates the pre-registered machine-readable
output requirement.

- Invalid file SHA-256:
  `abe26ce3d795cb8c947f90b00d7b5de326e6840dff15c1298514f90d34f932eb`.
- Superseding strict analysis:
  `../residual_diagnosis_v2_strict_json/DIAGNOSIS.json`.
- Superseding file SHA-256:
  `9303b8f8e6151c57618291d2edfd7bfb04d8d81654f439a7013768f035aaeaf9`.

The invalid files are retained rather than deleted or overwritten so the audit
history remains complete.
