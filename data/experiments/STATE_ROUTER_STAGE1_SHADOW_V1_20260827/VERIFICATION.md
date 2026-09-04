# Stage 1 Shadow 最终验证

- 日期：2026-08-27
- WSL：`UbuntuRecovered`
- 结果：实现回归通过；基础设施 canary 通过；分类 canary 失败；Stage 1 未毕业

## 代码与身份

- `FROZEN_CODE_MANIFEST.json`：69 文件，复验全部路径和 SHA-256 一致；manifest SHA-256
  `d2b9201d84f4bb81a71f9d547931c736c03f5a439e50228833847a4d643f0833`。
- canary 当时源码 archive SHA-256：
  `64829120e091710f103b64680175db19557cb62149a2544c051f1097ced4da6d`；69 文件。
- post-canary 当前代码 manifest SHA-256：
  `f2d0395159b28f9e2ab915cd3e6c82cea95ec1de2029dd610302e35b186074e8`；
  只修复未来 SQLite artifact 逻辑摘要/排除规则，没有重跑 canary。
- canary 数据：8 条，cases SHA-256
  `cf650d5c2af0011012c0d88780efc597c90ff392542e9b313d99408911426d53`。
- 本地引擎：`/home/chase/GitHub/vllm-rwkv`，HEAD
  `67f0c5996c50dca0ad779da545cb491527de988f`，worktree clean。
- 正式结果 SHA-256：
  `c078b641f21e3387e7352b1d20ca97fb37e954fd93b64cf67415efefd1270e48`。

## 命令结果

```text
uv run pytest -s --basetemp=/home/chase/GitHub/RWKV-LH/temp/pytest-stage1-final-full -q
=> 357 passed in 42.69s

uv run python -m compileall -q rwkv_lh scripts/run_long_horizon.py \
  scripts/run_state_router_shadow_canary_v1.py scripts/freeze_state_router_shadow_v1.py
=> pass

node --check rwkv_lh/web_assets/app.js
=> pass

uv lock --check
=> Resolved 43 packages

git diff --check
=> pass
```

实现冻结前聚焦测试为 31 passed；封装修复后聚焦测试为 10 passed。覆盖 runtime policy、机械输入投影、Harness metadata 行为
投影、Controller 透明返回、Observer 失败不干扰、并发追加/跨 run 隔离、共享产品入口、CLI、
Web request/API 和默认关闭兼容性。

## canary 与 artifact

- 正式 canary：8 条全部执行；route `3/8`、network `7/8`、OOD `1/1`。
- 基础设施：8/8 配对、8/8 menu digest 不变、16/16 record digest、influence 全 false、
  causal Shadow event 0、跨 run 混写 0、Controller exception 0。
- 8 个 SQLite 逻辑数据库 `integrity_check=ok`。
- 原 runner artifact manifest 因错误纳入 DB/WAL/SHM 物理文件而失效，原件保留为证据。
- `CANARY_LOGICAL_STATE_AUDIT.json` SHA-256：
  `2bfd8d5a4acd82f8052f886b467a835f02ba2f67bcda4157baa6ddbef3b52109`。
- `CANARY_STABLE_ARTIFACT_MANIFEST.json` SHA-256：
  `0d6f17e8880cc28c7f5b91924128abe772a80111354eac60d395d6948755a087`；
  33 个非 SQLite 稳定文件全部登记，SQLite 使用逻辑摘要。

本轮没有根据 canary 修改 Router/产品行为、样本、标签、PCA、head、阈值或指标。正式结果后
只修复了未来实验物理 SQLite manifest 的系统性缺陷，并保留原源码 archive 和原失败证据。
由于 route gate 失败且尚无 100 条审核有机轨迹，验证结论只能是“Shadow 基础设施完成，
Stage 1 未毕业”。
