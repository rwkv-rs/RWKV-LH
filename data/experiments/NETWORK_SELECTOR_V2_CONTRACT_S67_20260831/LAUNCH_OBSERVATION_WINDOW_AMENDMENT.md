# S67 remote launch observation-window amendment

The first launch recorder (SHA-256 `1e13e6e40041163cca39866a7c48806278d221b4f045d5e680e2b2dc02f0f6fe`) successfully started remote PID `3254910`, but required `train.py` after a fixed three-second observation. At that instant the same PID was still executing the hash/resource-checking bash launcher, so the recorder refused to write `launch.json`.

No second launch was attempted and the process was not interrupted. A read-only follow-up observed the same PID, parent PID 1, exec-replaced by the exact `.venv/bin/python train.py` command with the preregistered S67 dataset, output, seed, context, steps, LR, zero parent and GPU0 parameters. The remote output directory existed, the log showed seed 1067 initialization, and product port 18070 remained listening.

The recorder is corrected to poll the same PID for up to 15 seconds and never launches a replacement. A recovery recorder may now persist the already-running PID after revalidating preflight, launcher, process argv, product port and remote output. This changes only the observation window and audit persistence; it does not change training, data, state, model, optimizer, checkpoints, evaluation, or RWKV outputs.
