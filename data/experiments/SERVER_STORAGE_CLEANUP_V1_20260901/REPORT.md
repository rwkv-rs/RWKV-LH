# Server Storage Cleanup V1 — 2026-09-01

## Scope

- Host: `rwkv-260304` through SSH alias `rwkv-8222`.
- Filesystem: `/dev/nvme0n1p2`, mounted at `/`.
- Purpose: recover local NVMe space without stopping or changing the RWKV-LH production service, model weights, state profiles, training data, checkpoints, or experiment results.
- All inventory and cleanup commands were executed from WSL in `/home/chase/GitHub/RWKV-LH`.

## Pre-cleanup evidence

- Root filesystem: 3.7T total, 3.2T used, 291G available, 92% used.
- `/home/chase`: approximately 857GiB.
- The active RWKV-LH production process was PID `3383336`, serving port `18075` with:
  - weight `/home/chase/weights/BlinkDL__rwkv7-g1/rwkv7-g1i-13.3b-20260805-ctx16384.pth`;
  - engine `/home/chase/chase/vllm-rwkv-g6-cmix-r7-native-state-v1-20260831`;
  - production state root `/home/chase/chase/runtime/rwkv-g6-cmix-r7-native-state-v1-production-20260831`.
- No process command, working directory, or open file descriptor referenced the selected ReproBench cache/runtime targets.
- `/home/chase/.cache/uv/.lock` was held by three live `uv run` services, so the UV cache was explicitly excluded from deletion.

## Deleted targets

| Target | Allocated bytes before deletion | Classification | Recovery |
|---|---:|---|---|
| `/home/chase/chase/ReproBench/.cache` | 233,760,174,080 | Downloaded model, upstream and benchmark cache | Re-download/rebuild |
| `/home/chase/.cache/pip` | 8,926,846,976 | pip HTTP/package cache | Re-download |
| `/home/chase/.trash` | 7,294,959,616 | Already-discarded experiment copies | Permanently removed |
| `/home/chase/chase/ReproBench/.runtime` | 57,970,556,928 | Inactive generated benchmark runtimes/virtual environments | Rebuild |
| `/home/chase/chase/ReproBench/.benchmark-envs` | 9,700,806,656 | Inactive generated benchmark virtual environments | Rebuild |

Total allocated blocks removed: `317,653,344,256` bytes, approximately 317.7GB decimal / 295.8GiB.

## Explicitly preserved

- All files under `/home/chase/weights/`.
- All RWKV-PEFT datasets, outputs and checkpoints under `/home/chase/chase/RWKV-PEFT/`.
- RWKV-LH local datasets and model assets under `/home/chase/GitHub/RWKV-LH/`.
- ECRA data and experiment outputs under `/home/chase/RWKV-ECRA/`.
- The active vLLM environment, active engine source, native-state production runtime and state profiles.
- `/home/chase/.cache/uv/`, because live services held its lock.
- Historical trace archives and older model weights; they were not required to meet the storage target and were not deleted.

## Post-cleanup verification

- Root filesystem exact snapshot:
  - size: `4,030,220,222,464` bytes;
  - used: `3,212,516,331,520` bytes;
  - available: `612,903,317,504` bytes;
  - utilization: `84%`.
- `/home/chase`: `618,890,268,672` allocated bytes, approximately 576.4GiB.
- Deleted targets no longer exist; all explicitly preserved production paths still exist.
- PIDs `2297880`, `3319094`, `3320055`, and `3383336` remained alive.
- Ports `18070`, `18073`, `18074`, and `18075` remained listening.
- Port `18075` returned the expected model identity and a valid `rwkv-lh.native-state.v1` capability document.
- Capability assertions passed for create, resume, fork, commit, rollback, export and import.
- `prompt_replay=false`, `authoritative=false`, and `cache_role=disposable_acceleration` remained unchanged.
- The long-running UV-backed services on ports `5177` and `8787` remained alive; `5177` returned HTTP 200 and `8787` remained reachable with its root-path HTTP 404 behavior.

### Local tunnel restoration

The remote `18075` service was healthy after cleanup, but the local runtime manager initially contained a stale tunnel record for dead PID `126320`, so local port `29613` was not listening. This local process condition was independent of the deleted remote paths. Running `uv run rwkv-lh-stack up --timeout 60` recreated only the required SSH tunnel as PID `226995`; it did not start Web or worker processes and did not restart or mutate the remote model service. The restored local `29613` endpoint then passed model identity and the complete native-state capability probe.

## Result

The storage alert condition was reduced from 92% to 84% without stopping or mutating the active RWKV-LH deployment. No model weight, tuned state, training dataset, checkpoint, source tree, or experiment result was removed.
