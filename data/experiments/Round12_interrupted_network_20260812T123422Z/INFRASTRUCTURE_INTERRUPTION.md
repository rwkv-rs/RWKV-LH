# Round12 第五次基础设施中断

## 结论

本目录是 Round12 冻结实现的第五次独立启动副本，不计分、不续跑、不与其他运行合并。
每个本地 client TCP 已对应一条独立 SSH TCP，但同一公网路径整体恶化后仍出现成组
`RWKVOutcomeUnknownError -> RemoteDisconnected`。因此，共享 SSH tunnel 只是故障放大器，
不是唯一根因；单纯拆分 TCP 不能保证生成响应可取回。

## 启动前门禁

- 本地 socat 每接受一个 client TCP，就执行独立
  `ssh -W 127.0.0.1:18073`；明确 `ControlMaster=no`/`ControlPath=none`。
- 进程/socket 现场证明 8 个 client 对应 8 个 SSH PID 和不同公网 TCP 四元组。
- 重负载门禁：8 client × 3 batch × 2 request = 48/48、0 失败；prompt 14,117 chars，
  max_tokens=5000，实际 response 24,548 chars，请求延迟约 101–104 秒，批间空闲 30 秒。
- 门禁记录 `../Round12_pre_run/independent_ssh_long_response_multibatch_48.json`，SHA-256
  `754253d2ffa77ca97071a950fed8a4ec501e96e55cc7b294de31cb55f75e4a2a`。
- 门禁后 8/8 全新 SSH health 成功、远端 user unit 同 PID/零重启、ICMP 20/20。
- 全部门禁内容均为通用数字序列，不含 benchmark、答案、acceptance 或 reference。

## 中断现场

- `results.json` 43 行：blocked 32、interrupted 8、not_created 3；SHA-256
  `608017bc833990f026cb2ddb1bd9d9135cc59779c66064857b08d7715f11a20e`。
- cases 下有 59 份 audit；停止时并发 worker 仍有未归并结果。
- results 中 6 个 outcome unknown：`E2E-H03`、`E2E-LH08`、`E2E-LH09`、
  `E2E-LH10`、`E2E-B11`、`E2E-B12`。
- 另有两个真实非网络中断：`E2E-B02` 的 obligation replan priority=`high` 触发
  `int()` ValueError；`E2E-LH03` 的 failure-analysis decision 不在允许枚举内。
- 该次运行在 22 条 results/238 个模型请求时仍是 0 unknown；之后公网路径统一恶化，
  独立 SSH 会话仍在相近时间断开。这说明隔离 TCP 故障域能够延缓共享失效，但无法让
  已完成或正在生成的响应跨公网中断可靠交付。

## 停止与保全

确认 outcome unknown 后立即停止；等待 `ProcessPoolExecutor` 未快速退出，随后只对已核验
的精确进程组 150074 发送 TERM，并确认没有 Round12 worker 残留。原输出目录整体移动到
本目录。冻结源码未变，任何模型请求均未重发。

## 下一基础设施假设

下一次不得再以 live SSH stream 作为生成事务本身。透明恢复层必须：

1. 为每个合法模型调用分配唯一 job id；相同 prompt 的两次调用仍是不同 job。
2. 在远端先完整持久化原始请求，再对 localhost vLLM 只调用一次。
3. 在远端完整持久化原始响应；本地 SSH 中断后只按同一 job id 重新取回该响应。
4. 同 job id 重交必须验证原始请求 SHA 一致，并保持 `upstream_invocations == 1`。
5. 不解析 prompt/答案，不去重不同 job，不重试生成，不修改响应字节。

在主动杀掉取回 SSH 后，只有远端 invocation 仍为 1、最终响应 SHA 完全一致，才允许再次
启动 E2E。该传输恢复属于基础设施，不得改变 Controller、模型、sampling 或评价口径。
