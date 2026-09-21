# Active data after cleanup — 2026-09-21

Training, Agent evaluation and paid data generation are paused by owner.
No old trained State or historical training dataset is an approved input.

- datasets/rwkv_lh_real_project_dev_v1: 12 authored project development tasks; not training data or unseen holdout.
- datasets/rwkv_lh_real_agent_holdout_v2 and acceptance/: protected final acceptance; do not inspect, modify or delete.
- pipeline/sources/: a few real traces for offline pipeline development, not admitted training rows.
- test_fixtures/: minimal regression inputs, never use for data generation/training.
- runtime/ and models/downloads/: retained runtime resources, no old StateTune candidate promoted.
- test_runs/: disposable output from current software checks only.

Deletion inventory and SHA records: docs/cleanup/20260921/.
One frozen zero baseline and one run per candidate. No zero-a/zero-b, no default repeated runs.
