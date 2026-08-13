# Round12 第二次基础设施中断记录（不计分）

本目录是恢复原冻结 Round12 实现后，从空目录启动的第二次 90 题运行。它在公网
链路再次出现未知生成结果后主动停止，不是正式成绩，不得与任何其他运行合并或续跑。

## 事实与因果证据

- 固定参数：RWKV-E2E-90、并发 8、max transitions 200、冻结 Round12 实现。
- 停止后写入 55/90 个结果：External 9、Strict 0、Agent completed 0。
- 4 个 case 为 `RWKVOutcomeUnknownError -> RemoteDisconnected`；另 1 个 interrupted
  是预先登记但为保持单变量而未修的 `priority="high" -> ValueError` 协议边界问题。
- E2E-B24 的请求在 `2026-08-12T11:00:25.673+00:00` 开始，约 3.76 秒后
  `model_request_unknown`。同一窗口的远端 systemd journal 显示 vLLM 主进程持续运行、
  Running 约 8--14、Waiting 0，并持续返回大量 HTTP 200；无 OOM、进程重启或服务错误。
- 本地原 SSH 隧道 TCP 统计累计约 174 KB、158 次重传，拥塞窗口降至 2；随后 ICMP
  样本依次出现 15%、5%、22% 丢包。证据把未知结果归因到公网/SSH 传输，而不是模型
  服务过载或 Round12 witness 逻辑。

## 处置

- `results.json` SHA-256：
  `e5b04a64b918aeb346fcfce3c28f86469517bdccfc01be89761d686611893fb5`。
- runner 的已解析进程组被 TERM 关闭，父进程、8 个 worker 和 resource tracker 均退出；
  已生成的 audit、trace、event log、state timeline 和 workspace 原样保留。
- 输出整体从 `Round12/` 移至本目录，不读取其 acceptance 结果来指导生成，不复用任何
  case state 或模型输出。
- 后续建立指向同一 18073 的压缩 SSH 隧道 29614，并且只有在持续 320 请求 0 失败、
  压力后 50/50 ICMP 0% 丢包、health 约 198 ms 三项同时通过后，才允许再次从空目录启动。
