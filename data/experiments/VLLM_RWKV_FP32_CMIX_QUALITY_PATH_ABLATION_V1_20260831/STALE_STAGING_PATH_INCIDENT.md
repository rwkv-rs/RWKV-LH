# Stale staging path incident

The committed `run_fp32_cmix_dense/RESULT.json` was written while its output
directory still had the suffix `.pending`. Its per-case `raw_path` fields
therefore retain that staging component after the directory's atomic rename.
The raw files themselves were renamed atomically with the directory, remain
present under `run_fp32_cmix_dense/raw/`, and match every recorded
`raw_sha256`; no raw token, hidden, shift, WKV, or elapsed tensor was changed.

The first source-validation attempt discovered this before committing its
first case and was preserved as
`run_source_0501caa628967103490507d734f6a5efaf165794.failed_attempt1_stale_parent_projection_20260831`.
The validation runner now resolves only the final parent directory plus the
recorded basename, requires the recorded SHA-256 to match, and records both
paths and the correction flag. It does not rewrite the frozen ablation result.

This exposes a general atomic-output bug in experiment runners: artifact paths
must be rendered from the final output path, not the staging path. The shared
implementation pattern and all newly touched runners must be corrected and
regression-tested before final handoff.
