# Locked-test retirement amendment

The preregistration was correctly frozen before the tokenizer-boundary incident. A later read-only structural check parsed S67 test JSON, as recorded in `data/experiments/NETWORK_SELECTOR_V2_CONTRACT_S67_20260831/LOCKED_TEST_ISOLATION_INCIDENT_20260831.md` (SHA-256 `3ff6abe3163cedf81968f37e96ba34c0a5753d4f4f0c0b9f10c4a7dcd2a01c18`).

This ablation still skips test rows before JSON parsing and uses only train/dev. However, its reports must mark the old S67 test as retired rather than untouched, and no current candidate may claim a locked-test pass from those rows. A fresh independently registered S68 locked-test is required after unique dev selection.
