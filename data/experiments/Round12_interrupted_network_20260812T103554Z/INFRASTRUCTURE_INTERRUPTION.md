# Round12 基础设施中断记录（不计分）

本目录是 2026-08-12 第一次 Round12 正式启动的完整保留副本，不是 Round12
正式成绩，也不得与后续干净重跑合并或续跑。

## 事实

- 固定参数：RWKV-E2E-90、并发 8、max transitions 200、冻结 Round12 实现。
- 停止时 runner 已写入 63/90 个结果：blocked 31、interrupted 29、not_created 3；
  External 6、Strict 0、Agent completed 0。
- 29/29 个 `interrupted` 的直接错误完全相同：模型请求在可能完成后连接被远端关闭，
  记录为 `RWKVOutcomeUnknownError -> ConnectionError -> RemoteDisconnected`。
- 另有 E2E-LH01 在 obligation replan 中暴露 `priority="high"` 触发直接 `ValueError` 的
  通用协议边界缺陷。该问题是在 Round12 模型请求之后发现的，因此只登记为下一轮候选，
  不在 Round12 干净重跑前修复，避免改变预注册的唯一变量。
- E2E-LH02 的末端证据为 revision 142 `model_request_unknown`，随后 revision 143
  `run_interrupted`；它不是 transition budget 耗尽。
- 中断期间 `/models` 后来恢复返回，但只读 health latency 达到约 11,107 ms，明显高于
  正式启动前的约 256 ms，说明远端服务/转发存在抖动。
- 为避免其余 case 在不可靠连接上继续消耗，已向 runner 的已解析进程组 PGID 71952
  发送 TERM；父进程、8 个 worker 和 resource tracker 均已退出。

## 完整性与处置

- `results.json` SHA-256：
  `2e9e8c320e308fa9d92405d5e7321dfa960b80959c96d2b4860c86cf3a158cf0`。
- 已生成的逐题 audit、model trace、event log、state timeline、workspace、运行协议、
  runtime doctor 和 source-tree manifest 均原样保留。
- 原输出目录从 `Round12/` 整体移动为
  `Round12_interrupted_network_20260812T103554Z/`；没有删除或改写逐题结果。
- 后续必须在连接稳定检查通过后，以全新的 `Round12/` 从 90/90 开始；不得复用本目录
  的 state、workspace、模型输出或外部验收结果。
