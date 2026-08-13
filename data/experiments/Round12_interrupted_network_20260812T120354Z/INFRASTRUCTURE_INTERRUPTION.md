# Round12 第四次基础设施中断

## 结论

本目录是 Round12 冻结实现的第四次独立启动副本，不计分、不续跑、不与其他运行合并。
虽然启动前新的长连接/多批次门禁达到 288/288，但 E2E 仍在运行约 8 分钟后出现成组的
`RWKVOutcomeUnknownError -> RemoteDisconnected`。这推翻了“单条共享 SSH tunnel 经过
通用长连接压测即可承载 E2E”的基础设施假设。

## 启动前门禁

- 新 `ssh -NT -C` 隧道：本地 29616 → 同一远端 18073。
- 8 个持久 client × 3 批 × 12 请求，批次间空闲 30 秒，288/288、0 失败。
- 通用 prompt 14,086 chars，max_tokens=512，历时约 11 分 45 秒。
- 门禁记录：`../Round12_pre_run/fresh_tunnel_multibatch_288.json`，SHA-256
  `dbcdd6067b4fc7cea9d92972b42d76954a220e3a7df46d90a4e575c6d2361f07`。
- 门禁后 health=200；远端 vLLM user unit active/running、PID 3365670、NRestarts=0。
- 门禁提示不含 benchmark、答案、acceptance 或 reference。

## 中断现场

- `results.json` 有 40 行：blocked 26、interrupted 12、not_created 2；SHA-256
  `3fa8972c3296dfa2411eb2492fe4cc3f86bdac339120cff231acddbfce7c5a19`。
- cases 下有 61 份 audit；runner 并发 worker 尚在写入，所以多于 results 行。
- results 已写入 11 个 outcome unknown；audit 中共 15 个：`E2E-B27`、`E2E-B28`、
  `E2E-B30`、`E2E-H03`、`E2E-H10`、`E2E-LH01`、`E2E-LH02`、`E2E-LH03`、
  `E2E-LH04`、`E2E-LH06`、`E2E-LH09`、`E2E-LH10`、`E2E-LH11`、`E2E-LH12`、
  `E2E-M11`。
- 第一个 unknown 出现在 2026-08-12T12:02:19.324Z，之后约 74 秒内扩散到 15 题。
- unknown 横跨 `tool_choice`、`tool_action`、`task_decomposition`，对应 prompt 约
  3,777–19,080 chars、max_tokens 700/1800/5000；不是某一种协议请求独有。
- `E2E-H01` 另有真实模型协议中断：failure-analysis 两轮后仍未形成完整 JSON；该结果
  不是网络错误，但整轮已经被 transport unknown 污染，不能形成正式分数。

## 共享隧道失效形态

停止时精确检查显示：

- 共享 SSH PID 122908 及其主 TCP 仍为 ESTABLISHED；本地 8 个转发 channel 也仍为
  ESTABLISHED，但已经约 9 秒没有收发。
- 主 TCP 当时约 `bytes_sent=434467`、`bytes_retrans=5056`、`cwnd=7`；存在重传但连接
  没有被内核判死。
- 通过同一隧道访问带认证 `/v1/models`，5 秒没有任何响应并超时。
- 因此，一个共享 SSH TCP 的失效会同时传播到全部并发 direct-tcpip channel；
  ServerAlive 只能证明 SSH 控制进程尚未退出，不能证明每个转发 channel 可用。

## 停止与保全

确认 6 个 outcome unknown 后立即中断 runner；等待 `ProcessPoolExecutor` 未能快速退出，
随后只对已核验的精确进程组 132331 发送 TERM，并确认没有 Round12 worker 残留。原输出
目录整体移动到本目录。没有修改冻结源码，也没有复用模型响应或 workspace。

## 下一基础设施假设

下一步只改变透明传输拓扑：每个本地 HTTP client TCP 连接建立独立 SSH TCP 转发，避免
单条共享 tunnel 的队头阻塞/失效传播。转发层不得解析 HTTP、重试生成请求、缓存响应或
修改 payload/response；RWKV 模型、sampling、并发和 Controller 全部不变。必须先用
接近 E2E prompt/max_tokens 分布的纯通用数据执行长输出、多批次压力测试，并证明独立
SSH 会话数与本地 client 连接对应，再考虑第五次独立启动。
