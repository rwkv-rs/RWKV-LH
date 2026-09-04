# RWKV-LH real-chain v2 check

Date: 2026-09-04

Purpose: execute one real multi-step task through the current product entry point after the fresh current-subtask Selector architecture change.

Fixture source: deterministic project-local fixture created for this run.

Question: read `orders.json`, derive the count and total for paid orders, create exact `summary.json`, read it back, and report the verified path and values.

Expected operation progression: bounded observation, arithmetic derivation if needed, JSON write, read-back verification, audited finalization. The Planner and runtime remain authoritative; this expectation is only the test oracle and is not injected as a tool sequence.

No StateTune or model artifact mutation is permitted in this run.
