# Round46 Architecture Upload Validation

Date: 2026-08-14 (Asia/Shanghai)

## Uploaded architecture identity

Before the upload-only interface fix, all 62 files in
`Round46_basic30_decision_last_format/source_tree_manifest.json` matched the
formal Round46 run byte-for-byte (`0` mismatches). This verified that rejected
Round47--49 code had been fully reverted.

After the preregistered fix, the same comparison has exactly one mismatch:

| Path | Formal Round46 SHA-256 | Upload SHA-256 | Reason |
| --- | --- | --- | --- |
| `rwkv_lh/harness.py` | `1c76080fc016103926b383b3ef761493808c5e6e2e6f2332d649b89e0ce91b3f` | `bb0b976aaba6dda4260bcbdc3342bda940fd538cf392bff7e82b6f430f85eb4a` | Preregistered deterministic `python` alias resolution |

No Round46 Basic30 metric is recalculated or attributed to this interface-only
fix. The frozen model result remains Strict `23/30`, external `23/30`, agent
completed `25/30`, FP `2`, FN `0`.

## Validation results

| Check | Result |
| --- | --- |
| Targeted canonical `python` alias regression | `1/1` passed |
| Full offline pytest | `364/364` passed in 31.71 s |
| LH-Control after fix | `30/30` passed |
| RWKV-E2E catalog validation | `90/90`, `catalog_valid=true` |

The first two pytest launch attempts inherited Windows `TMP`/`TEMP` paths and
failed in pytest capture cleanup before running assertions. The authoritative
run used the repository-owned WSL path
`/home/chase/GitHub/RWKV-LH/temp/pytest-upload-validation` as `TMPDIR`. It
executed all 364 tests. This changes only the test process temporary directory,
not product behavior or evaluation criteria.

LH-Control artifacts are stored under
`Round46_upload_validation/lh_control_30_after_alias_fix/`. Per-case runtime
databases and workspaces remain local under the repository's existing ignored
audit-data policy; the aggregate report and results are versioned.

## Scope boundary

`Round50_PROTOCOL.md` describes an unexecuted future candidate. It is excluded
from this architecture upload so that the Git checkpoint represents completed,
validated work only.
