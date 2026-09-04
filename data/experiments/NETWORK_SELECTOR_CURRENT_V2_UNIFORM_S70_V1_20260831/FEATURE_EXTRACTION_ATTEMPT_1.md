# S70 feature extraction attempt 1 — runtime import preflight failure

Date: 2026-08-31 (Asia/Shanghai)

The first command used the project `uv` interpreter without exposing the pinned
quality engine's Python environment.  The extractor completed dataset, engine,
model, attestation, GPU, and remote-service preflight, then failed on lazy
`import vllm` at the first requested bootstrap forward.

No bootstrap/current/history forward completed; no hidden state, logits, model
text, shard, or metrics were produced.  The empty pending directory was retained
as `run_zero_train_dev_features.failed_runtime_import_20260831`.

The rerun changes only process activation: it uses the pinned engine venv and an
explicit project+engine `PYTHONPATH`.  Dataset, zero state, model, engine commit,
WKV profile, GPU0, extraction algorithm, and acceptance gates are unchanged.
