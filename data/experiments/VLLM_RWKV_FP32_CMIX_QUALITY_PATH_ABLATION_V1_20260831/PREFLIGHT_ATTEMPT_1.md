# Preflight attempt 1

The first `fp32_cmix_dense` invocation stopped before the first diagnostic
forward because changing the row thresholds cannot override the explicit
`rows == 1` branch in `select_path`. No case, raw hidden, state tensor, metric,
or result was produced. The empty staging directory was preserved as
`run_fp32_cmix_dense.failed_preflight_select_path_20260831`. The runner was
corrected to replace only the runtime `select_path` function with the exact
`PathConfig(rows=B*T, cmix_mode=CMIX_DENSE)` specified by the preregistered
variant; thresholds and comparisons are unchanged.
