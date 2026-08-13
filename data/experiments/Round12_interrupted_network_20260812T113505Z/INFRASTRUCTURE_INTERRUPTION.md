# Round12 第三次基础设施中断

## 结论

本目录是 Round12 冻结实现的第三次独立启动副本，不计分、不续跑、不与任何一次运行
合并。runner 在首次发现并确认 `RWKVOutcomeUnknownError -> RemoteDisconnected` 后停止，
原输出目录整体移动到本目录；没有复用其中 workspace、模型响应或 case 结果。

## 中断现场

- 启动入口：`127.0.0.1:29614`，SSH `-C` 压缩隧道转发到同一远端
  `127.0.0.1:18073`。
- 冻结实现、模型、sampling、并发 8、16K context、transition 上限 200 均未改变。
- 停止时 `results.json` 有 39 行，cases 下有 55 份 audit；runner 仍有并发 worker，
  因此两者数量不同。
- 状态分布：blocked 29、interrupted 7、not_created 3。
- 6 个连接结果未知：`E2E-H03`、`E2E-LH08`、`E2E-LH09`、`E2E-LH10`、
  `E2E-LH11`、`E2E-B11`。
- 另有一个真实模型协议中断 `E2E-H01`：失败恢复分析连续返回不在
  `retry_same/reselect_action/replan` 集合内的 decision。它不是网络错误，但由于整轮已经
  被 transport outcome unknown 污染，同样不得形成 Round12 分数。
- `results.json` SHA-256：
  `546ef44afa50b3215f6f37153d398d05eba42a6a664ad5e236467a5bbb0a0e94`。

## 停止与保全

首次确认 4 个 outcome unknown 后向 runner 发送中断；因
`ProcessPoolExecutor.shutdown(wait=True)` 仍等待 worker，再对已核验的精确进程组
`108178` 发送 TERM。随后确认没有 `rwkv-lh-e2e`/Round12 worker 残留，才整体重命名
输出目录。该操作只终止已污染的实验进程，没有修改冻结源码。

## 中断后的只读诊断

- 公网 ICMP 20/20，0% 丢包，RTT 约 34.2–34.9 ms。
- 原压缩隧道进程仍存活，但本地 `/v1/models` 10 秒无任何字节并超时；说明 SSH
  control connection 存活并不能证明新 forward channel 可用。
- 一个新建 SSH 会话曾成功连接：远端 18073 在约 1.6 ms 返回 401（未提供 API key，
  属于预期认证响应），`ss` 显示 PID 3365670 的原 vLLM 进程仍监听 18073。
- 首次误用系统级 `systemctl` 查询同名单元，得到 `inactive/dead`；随后从 PID cgroup
  确认它实际属于 user unit，并改用 `systemctl --user` 复核：`active/running`、
  `NRestarts=0`、`MainPID=3365670`，自 2026-08-08 11:53:05 CST 起未重启。因此该项不是
  服务切换，而是诊断命令作用域错误；更正记录予以保留，不能用错误的首次查询支撑结论。
- 对应 user-unit journal 在中断窗口持续记录 `/v1/completions` HTTP 200、Waiting=0，
  与本地 `RemoteDisconnected` 同时存在，进一步把故障边界缩小到 vLLM 响应之后、
  本地客户端之前的 SSH/网络转发路径。
- 随后的新 SSH 连接又在 banner exchange 阶段超时，证明网络/SSH 入口仍不稳定；因此
  不能仅凭一次 ICMP 0% 或一次远端 health 成功立即重跑。

## 对当前结构假设的验证边界

本次样本可以用于验证此前断点的结构复现，例如 witness intent、obligation、恢复协议和
proof 自比拒绝；不得用于验证正确率或上传门禁。它还推翻了“SSH 压缩隧道已足以保证
90 题长运行稳定”的基础设施假设。下一次独立启动前至少需要：重新建立干净隧道、
确认远端 user-unit 监管状态、执行带认证 health、执行覆盖长连接/多批次/空闲复用的通用生成
压力测试，并在测试后再次确认旧连接没有挂起 channel。
