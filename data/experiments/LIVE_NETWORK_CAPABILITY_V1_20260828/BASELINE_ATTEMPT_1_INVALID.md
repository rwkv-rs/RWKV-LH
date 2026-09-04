# Baseline attempt 1 — invalid evaluator

首条 `NET-V1-URL-EXAMPLE` 已经通过真实公网路径取得内容并写入不可变 snapshot/route，随后诊断器
调用了 `SnapshotStore` 不存在的 `load()` 方法并异常退出。该次尝试没有形成 `RESULT.json`，不得
计为基线通过或失败。

修正仅发生在独立的 `temp/diagnose_live_network_preflight_v1_r2.py`：使用现有
`read_clean(snapshot_digest)` 回读 clean 内容并重新计算 SHA256。数据集、请求参数、Provider、
固定指标和通过阈值均未修改；第二次运行使用新的输出目录，不复用第一次 route 缓存。
