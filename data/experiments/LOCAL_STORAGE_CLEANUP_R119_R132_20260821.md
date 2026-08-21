# R119–R132 本地冗余状态清理记录

日期：2026-08-21  
执行环境：WSL `UbuntuRecovered`，项目根目录
`/home/chase/GitHub/RWKV-LH`。

## 清理对象

只清理下列已完成或已明确判无效的 R119–R132 运行根目录，以及相同轮次的 `outputs/`
重复运行目录中的逐题 SQLite 状态文件：

- 精确允许文件名：`long_horizon.db`、`long_horizon.db-shm`、`long_horizon.db-wal`；
- 精确位置：显式登记的 25 个 run root 下 `cases/<case>/state/`；
- 前置条件：run root 必须有 `results.json`，对应 case 必须有已导出的 `audit.json`；
- 不删除 `audit.json`、workspace、round-level results/report/protocol/source manifest、源码或测试。

清理脚本：
`/home/chase/GitHub/RWKV-LH/temp/cleanup_r119_r132_redundant_sqlite_state_20260821.py`。
脚本先 dry-run，再要求执行时提供完全相同的 expected file count 与 expected bytes；解析后的
目标必须位于显式 run root 内且文件名在 allowlist 中。

## 结果

- 删除文件：**2,267**；
- 删除字节：**190,770,888,944 bytes（177.669 GiB）**；
- 执行后同口径残留：**0 files / 0 bytes**；
- 因缺少完整 `audit.json` 而保护性跳过：**45 files**，全部来自 R130 资源崩溃/传输中断
  现场；没有删除这些未完成导出的唯一状态。

磁盘变化：`/dev/sdd` 从约 **855 GiB used / 101 GiB available / 90%** 变为约
**679 GiB used / 278 GiB available / 71%**。

## 保留与可恢复性

- R119–R132 精选的 128 个 round-level 证据文件及 upload manifest 均保留；本地数据提交为
  `f5d9c10f868d30d66b325e56aa44a327d2df2fd9`。
- R132 的 90 个逐题 `audit.json` 全部仍存在；关键 round 的 `results.json` 均通过 JSON
  复核。
- 删除的 SQLite 文件不进入 git，且只能通过固定源码/参数重新运行恢复；其已导出的审计、
  结果和因果结论不受影响。
- 其他 dirty worktree、源码、未提交数据集和历史轮次没有被本次清理修改。

## 远端说明

精选数据提交已创建但未上传：仓库 `.git/hooks/pre-push` 固定拒绝 push，并输出
`RWKV-LH is in local-only development mode; push is disabled.`。本次清理没有绕过该策略；
远端 `origin/chase/g1i-tool-protocol` 仍停在清理前的 `7a66cf9`。
