# 当前 Zero 服务就绪审计

2026-09-07 06:23:42 UTC 完成远端核验。运行时身份与 SSH 转发检查通过；本次未运行 Agent 题目、未请求模型生成，不判断强模型上游是否稳定，也不代替新双零运行冻结。

- Executor 服务 `rwkv-lh-current-zero-executor-20260907.service` 为 active/running，MainPID 1486276；Selector 同名角色服务 MainPID 1476735。审计前后 PID、启动时间和服务状态不变。
- SSH 进程 1269095 将本地 `29613 → 18234`、`29621 → 18239`，均绑定 loopback。两端 GET models / capabilities / healthz 返回正常；本地与远端 Selector 身份及 native capabilities 一致。
- main engine 全部 **6395 文件 / 145117170 字节**、selector-clean 全部 **6386 文件 / 131275931 字节**，经当前生产 `_validate_engine_source_manifest` 校验实际文件集合、逐文件 SHA 与大小；清单自身 SHA 使用已冻结登记值，未以现场自算 SHA 代替预期身份。完整 scope 仅排除 `.git`、`.venv`、`__pycache__` 目录。没有执行 Git；Git clean 状态保持 unknown。
- 两份现存 safetensors 均重新完整计算 SHA，匹配模型 manifest；计算前后 inode / bytes / mtime 不变。模型 manifest 与 config SHA 也匹配原登记。**13.3B 客户端身份取 manifest 的原始 PTH 来源 SHA，Selector 取转换后 safetensors SHA**；本次没有验证原始 PTH 文件是否仍存在。
- Selector decoder manifest 经生产 loader 通过，health 返回当前 `selector-intent.v4`、既定 trie decoder、`profile_id=zero`、profile SHA 与 manifest SHA 全零。两个本项目服务的实际进程中均未设置训练 State profile manifest；只记录指定公共环境键，没有输出环境或密钥。13.3B native-state GET 能力声明正常。未读取任何 State 张量或缓存内容，不能把 GET 描述成实际零态生成验证。
- 本地核验时的全部 `rwkv_lh/*.py` 与服务器文件集合及 SHA 一致。Executor launcher 按上一连接轮仅加错误日志后的快照比对，Selector launcher / decoder 按原上传冻结身份比对，均一致。
- GPU0 / GPU1 分别占用 28463 / 7581 MiB；GPU2 另项目进程 3979071 仍占用约 37910 MiB，GPU3 仅 15 MiB。采样时四卡利用率均为 0。项目所在文件系统可用 686385975296 字节。未停止、重启或改动任何进程。

| 身份 | SHA-256 |
| --- | --- |
| main engine source manifest | `5c906f8c7c40b96f4a78752131e877726e93f08664df282867fabd43aed47bfa` |
| selector-clean source manifest | `7ee8d7f5bccb4ff6bee2d2fd38f96365931c57abffc65e7c70fad0f8c6bcb21b` |
| 13.3B 现存 safetensors | `a5b4fbab12ce321f57ba0e9a00ddf32e5b3644f8b50216cc6ef14aba841efefd` |
| 2.9B 现存 safetensors | `c1a316e75abd50f5edc3358fbb2c7d1cb18c611d9b2aa5b888091c8d45cc866c` |
| 当前 decoder manifest | `9049329c79e89f057e2631bdba7cae771074e025c1df8b23bd4494e4f36f776b` |

可复核原始证据：

- `RUNTIME_AUDIT_EXPECTATIONS.json`：`39bec4adb586f065d785782d7ea445e82e1f6a2a7493bd923bb5b3577d8d1f9b`。
- `RUNTIME_REMOTE_READINESS.json`：`d3e6b9a1eeef1584a092a886dc00f332c18d41692828e8a77159b54d9b52f3b0`。
- `RUNTIME_LOCAL_TUNNEL_READINESS.json`：`4e65a744fbd8cbbc7fdae4e96ee6c42ad1663b4cffa3d0803cbf2132271ec5a6`。
- `RUNTIME_READINESS_SCRIPT.py.snapshot` 与 `temp/audit_strong_upstream_runtime_readiness_20260907.py`：`c86e53040db99a44ccad14417f16f419323d286d5701e150ebb9918a417ae895`。远端只上传并运行此临时诊断脚本，未覆盖旧冻结工件。

脚本与全部证据的校验清单为 `RUNTIME_READINESS_SHA256SUMS`。未读 Holdout、confirmation、`data/acceptance/` 或 SQLite；未改配置、依赖、生产源码或服务。
