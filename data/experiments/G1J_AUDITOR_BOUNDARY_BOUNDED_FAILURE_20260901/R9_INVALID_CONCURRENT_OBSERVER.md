# R9 基础设施无效中止记录

日期：2026-09-01。R9 启动后只读进程检查发现 R8 的 `uv/python` 子进程没有随 PTY Ctrl-C 退出，
R8 与 R9 短时同时请求同一 G1J 服务，违反预登记的 `concurrency=1`。R8 benchmark PID
`588603/588628` 与 R9 PID `592314/592321` 已精确 SIGTERM，未触碰其他进程。R9 目录保留，禁止进入
能力统计或 State Tune 数据。
