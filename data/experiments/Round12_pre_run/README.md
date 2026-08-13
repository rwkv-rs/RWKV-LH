# Round12 正式运行前冻结记录

记录日期：2026-08-12。此目录只包含离线产品测试、确定性架构控制集和
Round11 冻结工作区上的 witness catalog 容量审计；尚未向 RWKV 发出任何
Round12 正式 E2E 请求，也没有读取 Codex reference 或 hidden acceptance 来生成、
过滤、排序或选择 witness。

## 预注册与唯一变量

- 预注册协议：`../Round12_PROTOCOL.md`
- 协议 SHA-256：`18afdaedf663b95e6246b9b4f4b0072747df13112ff297f952f553cfd651b9ac`
- 唯一变量：`rwkv_witness_intent_lifecycle.v1`
- 模型、sampling、Goal/action/obligation/final 策略、90 题数据、外部验收、并发 8
  和 max transitions 200 均保持 Round11 口径。

实现边界是：RWKV 在具体 action 已选择、但尚未 `attempt_started` 和执行之前提交
WitnessIntent；动作结束后，运行时完整枚举作用域内的结构合法来源和 transform，
RWKV 先选择原始来源 `WS-*`，再选择该来源下的派生句柄 `WH-*`。Controller 只做
schema/scope/ID 校验和逐字展开，不试探其他候选，不修改 RWKV 最终答案。

## Witness catalog 全 90 题容量审计

- 数据：Round11 的 90 个冻结 workspace，加三份公开 `tasks.json`。
- 版本：RWKV-E2E-90 v1；Round11 results SHA-256
  `dedcc2db250b3a563d5cb6271596a2a941a4ca6900452cdf631b24164fbeedbf`。
- 用途：在正式模型运行前验证目录完整性、结构合法性、16K 上下文边界和确定性。
- 生成命令：
  `TMPDIR=/home/chase/GitHub/RWKV-LH/temp TMP=/home/chase/GitHub/RWKV-LH/temp TEMP=/home/chase/GitHub/RWKV-LH/temp uv run python /home/chase/GitHub/RWKV-LH/temp/audit_round12_witness_catalog_bounds.py --output /home/chase/GitHub/RWKV-LH/data/experiments/Round12_pre_run/witness_catalog_bound_audit.json`
- 结果 SHA-256：`1ecf4a1f5be29d588311e44e6cbf0649cd60844c4a69121537134dae6b4f9a6a`；重复生成一致。
- 覆盖：90/90；最大完整 handle 数 810（E2E-H02）；最大原始来源提示约 7,031
  tokens（E2E-H05）；选择一个原始来源后最大派生句柄提示约 8,935 tokens
  （E2E-H14），均未截断且低于 16K。
- 审计文件明确记录 `acceptance_or_reference_read=false`。目录生成器不接收 criterion
  描述、acceptance、reference 或相似度输入。

## 离线测试与 LH-Control

最终冻结源码执行：

```text
TMPDIR=/home/chase/GitHub/RWKV-LH/temp TMP=/home/chase/GitHub/RWKV-LH/temp TEMP=/home/chase/GitHub/RWKV-LH/temp uv run pytest -q
201 passed in 13.52s

TMPDIR=/home/chase/GitHub/RWKV-LH/temp TMP=/home/chase/GitHub/RWKV-LH/temp TEMP=/home/chase/GitHub/RWKV-LH/temp uv run python /home/chase/GitHub/RWKV-LH/scripts/run_lh_control_benchmark.py --output /home/chase/GitHub/RWKV-LH/data/experiments/Round12_pre_run/lh_control_30_ready
30 passed, 0 failed

TMPDIR=/home/chase/GitHub/RWKV-LH/temp TMP=/home/chase/GitHub/RWKV-LH/temp TEMP=/home/chase/GitHub/RWKV-LH/temp uv run rwkv-lh-e2e --suite all --validate-only
RWKV-E2E-90: 90 selected, catalog_valid=true
```

- 最终 LH-Control results SHA-256：
  `8e2474a167a0904d2d3347e19097c9e56bbe017af3f0dea2171b73c6afcda8e3`。
- M04 真实经过 `witness_intent_precommit`、`witness_validation`、
  `witness_handle_binding`，proof=true，并提交 `source.txt#L2-L2`。
- 新增的事件顺序回归固定 `action_selected < witness_intent_precommit_started < attempt_started`；
  intent 能看到 RWKV 自己选择的具体 action，但看不到 action result。

第一次控制集结果保留在 `lh_control_30/`，为 29/30，SHA-256
`75a6c9a72031fa7f7879d420b2a66bbe75e81b889ed537f5eb2b466b78bc1d92`。
唯一失败 LH-M04 是旧 Round11 `SequenceClient` 仍返回 validation.v4/binding 响应，
无法满足 Round12 的 precommit 协议；它不是产品 RWKV 运行结果。修复夹具后 `lh_control_30_final/`、
`lh_control_30_frozen/` 和最终 `lh_control_30_ready/` 均为 30/30，失败记录没有被覆盖。

## 冻结核心文件摘要

| 文件 | SHA-256 |
| --- | --- |
| `rwkv_lh/controller.py` | `5cd25f669ea82eca75bedaea1d98f9e0e2d68328b187a69182bc423845e838e5` |
| `rwkv_lh/model.py` | `db71a604231fac29b5023b40f0855d849b6f34da9eeaded48b6546481b45dbc1` |
| `rwkv_lh/schema.py` | `d2a5ff9addf036b6cb0e64c60dbf71d7f2fd19130820052c20fbbe9feec19b43` |
| `rwkv_lh/store.py` | `d7203c0e779b25055a2e91dd0e5def792a0bf66954be233b6e638ec87e58ac05` |
| `rwkv_lh/proof.py` | `b58fa752c41ba773260c52c826cfe0002ead3e39eafd0ab52bb97529794ddabd` |
| `rwkv_lh/witness.py` | `a5293cbaa39f1471765e828eaa3afa762393ccce7c84be4634e1faef0f4a2a14` |
| `rwkv_lh/temp_policy.py` | `c82a849cc7737e2bc497e888f9991a920b4d94a3d0e0f86aae78858d226c33f1` |
| `scripts/run_rwkv_e2e_benchmark.py` | `c1d5c72550788c53826ab8a332c7a2ab6265a2353d236b2442a7c6a7a9ba47a8` |
| `scripts/run_lh_control_benchmark.py` | `6408bd6cc98d1fdbc467f13324e5b478a7e1633a650bc15c52da87ff134e31e0` |
| `tests/test_witness_lifecycle.py` | `6b9e495b3cddc6e52c7b8ad17b274f2459945f056b6eb6964ba6fbdc72e0bbaf` |

正式 runner 还会在 Round12 输出目录中生成完整 source-tree manifest、运行协议、
endpoint doctor、逐题 audit/model trace/event log/state timeline 和逐文件摘要；这些才是
正式结果对应的完整实现权威记录。

## 网络中断后的重启门禁

第一次正式启动在 63/90 时停止，29 个 case 的末端均为
`RWKVOutcomeUnknownError -> RemoteDisconnected`。污染输出整体保存在
`../Round12_interrupted_network_20260812T103554Z/`，不得计分、合并或续跑。

随后使用完全不含 benchmark、acceptance、reference 或答案的通用短提示，对相同生成
endpoint 做并发 8 检查：8/8 返回非空结果，无连接未知。记录文件
`restart_endpoint_readiness.json` 的 SHA-256 为
`0578fe19f1d6fd5d3c58b03ab645748fcb8f6f6d511371fe1da513efd2955fa7`，其中明确登记
`benchmark_or_acceptance_or_reference_read=false`。由于检查后 `/models` 延迟仍约 10 秒，
干净重跑还必须等待健康延迟回落并再次通过只读 health；不能只凭端口存在就立即重启。

最终重启检查保存在 `restart_endpoint_readiness_stable.json`，SHA-256
`b75535dfd1bde7f91dce048ddca4a259675d426a30b29ebb3647e3ae45856d45`：health before/after
分别约 340/516 ms，并发 8 个真实生成请求 8/8 成功、约 1.24 秒，无未知结果。恢复原冻结
实现后产品测试重新为 201/201，`lh_control_30_clean_restart/results.json` 为 30/30，
SHA-256 `8f12be9909be330e436c6a4a2b4ece50d63669040305edb70a8385869988c1b5`。

第二次干净启动在 55/90 时再次出现 4 个 `RemoteDisconnected`，完整副本保存于
`../Round12_interrupted_network_20260812T110102Z/`，其 results SHA-256 为
`e5b04a64b918aeb346fcfce3c28f86469517bdccfc01be89761d686611893fb5`，同样不计分。
远端 systemd journal 证明 vLLM 主进程未重启、Waiting=0 且同期持续 HTTP 200；本地旧
SSH 连接则有约 174 KB/158 次 TCP 重传，ICMP 一度为 22% 丢包。

为减少相同长提示在不稳定公网中的传输暴露，建立指向同一远端 18073 的 SSH 压缩隧道
`127.0.0.1:29614`；这只改变传输编码，不改变请求 payload、模型、sampling、并发或输出。
通用提示的同一 session 空闲复用测试为 40/40，记录 SHA-256
`bf354d2dac71da675f12a14fe817ed372aa5c321ad433d1b512c4de47993659d`。网络恢复后持续
压力测试为 8 worker × 40 = 320/320、0 失败，延迟 min/median/max 为
2948.5/3790.45/5861.5 ms，记录 SHA-256
`c01da87274908b522b03c7563a24567597ec301fa82d337313ce6831eee5680e`。压力结束后
ICMP 50/50、0% 丢包，29614 health 约 198 ms；两个 JSON 都登记
`benchmark_or_acceptance_or_reference_read=false`。

## 中断样本的非计分向后因果分析

在第三次冻结运行期间，前两次中断目录仅被作为故障样本分析；没有读取标准答案、
`external_checks`、`external_passed`、`passed`、runner verifier observation 或最终答案。
分析使用 `results.json` 的运行计数/状态白名单，以及各 case 的 lifecycle、协议、动作、
Goal obligation、witness、proof 和持久状态事件。两次运行仍然彼此独立，未合并、未续跑、
未形成 Round12 分数。

- 生成脚本：`../../../temp/analyze_round12_interrupted_backward_causality.py`。
- 逐题结构化结果：`interrupted_attempt_backward_causality.json`，纳入第三次中断样本后的
  最新 SHA-256 `f1e4a1adcb0432d4b9e25193c15ff86cba096c5c78a3b2cfe5a9d194ad27aee3`。
- 人读报告：`INTERRUPTED_ATTEMPT_BACKWARD_CAUSALITY.md`，纳入第三次中断样本后的
  最新 SHA-256 `cdcf8a51bea62ad60d79b4da7a9c5ee88203f671d09477dcb8da8ee292132e7d`。

前两次样本分别有 87/71 份 audit；第二次在网络较稳定、执行得更深时，终态归因为
`witness_intent_contract` 的题数从 16 增至 27，12 个共同题目两次都复现该根因。
第二次只有 2 题到达 witness catalog/binding，4 个 proof 评估事件全部为 false；其中
已观测到 RWKV 把 actual 和 expected 选为同一证据源，确定性 proof 因来源不独立而拒绝。
这说明传输故障会遮蔽系统断点，但不是 witness/obligation/恢复协议断点的原因。

第三次冻结运行完成后，必须用同一脚本独立分析正式目录，验证 transport unknown 是否
归零、相同协议断点是否复现、proof 拒绝是否可追溯，以及 obligation replan 是否继续
放大请求/恢复预算。它只能验证当前冻结实现，不能验证运行启动后提出的任何代码改动。

第三次独立启动在 39 条 results/55 份 audit 时再次出现 6 个 outcome unknown，整体保存于
`../Round12_interrupted_network_20260812T113505Z/`，results SHA-256
`546ef44afa50b3215f6f37153d398d05eba42a6a664ad5e236467a5bbb0a0e94`。它不计分，但用同一
分析器再次观测到 3 题进入 witness catalog/binding；`E2E-M01` 在与 B15 不同的任务上复现
了“intent 两侧同为 dependency artifact → RWKV 对两侧选择同一个 source/handle → proof
拒绝同源自比 → local revision 后 intent 合约失败”的完整链。因此，同源自比不是 B15
单题偶然，也不是标准答案比较产生的诊断。

第三次运行同时推翻“压缩隧道足以保证完整 90 题长运行”的基础设施假设：中断后 ICMP
20/20 正常，但旧 tunnel health 超时；新 SSH 会话一度能直接访问远端 18073，随后又在
banner exchange 超时。详细现场见该目录的 `INFRASTRUCTURE_INTERRUPTION.md`。

清理旧隧道后，在新本地端口 `29616` 建立全新 `ssh -NT -C` 转发，并纠正服务监管诊断：
该 vLLM 实际属于 `systemctl --user` 单元，复核结果始终为 active/running、PID 3365670、
NRestarts=0；此前系统级 `systemctl` 的 inactive 结果是作用域错误，已在第三次中断文档中
保留并更正。

第四次独立启动前的新门禁为 `fresh_tunnel_multibatch_288.json`，SHA-256
`dbcdd6067b4fc7cea9d92972b42d76954a220e3a7df46d90a4e575c6d2361f07`。它使用 8 个持久
client、3 批、每批每 client 12 次，共 288/288 通用生成；批次间空闲 30 秒后复用原 client，
输入 14,086 chars，max_tokens=512，历时约 11 分 45 秒，0 失败，延迟 min/median/max 为
14317.9/19893.5/27951.9 ms。提示和记录均不含 benchmark、答案、acceptance 或 reference。
门禁后带认证 health=200、约 86 ms，远端 user unit 仍为同 PID、零重启。

第四次独立启动仍在约 8 分钟后出现成组断连，整体保存于
`../Round12_interrupted_network_20260812T120354Z/`。其 results 为 40 行，SHA-256
`3fa8972c3296dfa2411eb2492fe4cc3f86bdac339120cff231acddbfce7c5a19`；audit 中共有 15 个
case 记录 outcome unknown，集中在约 74 秒内，横跨 tool choice、tool action 和 task
decomposition。停止现场显示共享 SSH 主 TCP 和 8 个本地 channel 仍为 ESTABLISHED，
但同 tunnel health 完全无响应。因此下一门禁改为每个本地 client TCP 使用独立 SSH TCP，
不允许解析、重试、缓存或修改 HTTP；详细证据见该目录的 `INFRASTRUCTURE_INTERRUPTION.md`。

下一传输拓扑由 `temp/ssh_stdio_to_rwkv_18073.sh`（SHA-256
`5143c06bca42282d8da6ec1c533f29a63076061a3e35a9d78bf9b80463328ee4`）和本地 socat
listener 组成：每个被接受的本地 HTTP client TCP 创建独立 `ssh -W 127.0.0.1:18073`，
明确设置 `ControlMaster=no`/`ControlPath=none`。它只搬运字节，不解析 HTTP，不重试生成，
不缓存、增删改 payload 或响应。进程与 socket 检查实证 8 个 client 对应 8 个 SSH PID、
8 条不同公网 TCP 四元组。

接近 E2E 最重请求形态的门禁为 `independent_ssh_long_response_multibatch_48.json`，SHA-256
`754253d2ffa77ca97071a950fed8a4ec501e96e55cc7b294de31cb55f75e4a2a`：8 个持久 client、
3 批、每批每 client 2 次，共 48/48、0 失败；批次间空闲 30 秒，prompt 14,117 chars，
max_tokens=5000，每次实际响应 24,548 chars，单请求约 101–104 秒，历时约 10 分 50 秒。
提示仅要求生成通用整数序列，明确不含 benchmark、答案、acceptance 或 reference。
门禁后 8/8 新建独立 SSH health 均为 200，约 0.63–0.68 秒；远端 user unit 为同 PID、
NRestarts=0；随后 ICMP 20/20、0% 丢包。第五次运行只能使用这一透明拓扑。

第五次独立启动仍在 43 条 results 时出现 6 个 outcome unknown，整体保存于
`../Round12_interrupted_network_20260812T123422Z/`，results SHA-256
`608017bc833990f026cb2ddb1bd9d9135cc59779c66064857b08d7715f11a20e`。这推翻了“独立 SSH
TCP 足以解决”的假设：它隔离共享 tunnel 故障域，但不能抵抗整个公网路径恶化。下一门禁
升级为远端单次生成事务落盘：每个合法调用有唯一 job id，请求/响应原始字节远端持久化，
公网断线只按同 id 取回既有响应，绝不重发 vLLM；相同 prompt 的不同合法调用不得去重。

该事务恢复层已实现并通过预启动门禁：

- 远端 spool：`temp/rwkv_remote_generation_spool.py`，SHA-256
  `461b647e60d84dd5d75e0b4fb3556bf6e4e6108dd854180c6ac92e72689d34ae`。
- 本地透明代理：`temp/rwkv_durable_transport_proxy.py`，SHA-256
  `ac6912c2ee03686efeea16a85f8be7afdad87e701867f10b0f82d3c4b94efedd`。
- 远端 job root（门禁专用）：
  `/home/chase/rwkv_lh_transport/round12_20260812T124000Z`；spool user unit 为
  `rwkv-round12-spool-20260812.service`。
- 本地代理只生成唯一 job id、校验 request/response byte SHA 并重取同一 job；它不解析
  prompt 或模型答案，不按 prompt 去重，不重发 vLLM，不修改响应字节。
- 如果同一 job 在 850 秒内仍无法取回，代理返回非重试状态 HTTP 424；冻结运行时只会
  自动重试 425/429/500/502/503/504，因此不会把“已生成但尚未取回”误当成新调用并创建
  第二个 job。该保护只约束传输失败，不接触或改写模型输出。

门禁包含 17 个通用 job：

1. 同一 request SHA 的 8 个合法调用具有 8 个不同 job id、8 个不同模型响应，逐个
   `upstream_invocations=1`，证明没有按 prompt 去重。
2. 单个长请求生成期间主动终止第一次 SSH，第二次以同 job id 取回；远端 invocation=1，
   远端/本地 raw response SHA 同为
   `9968f78bb82b68179b5fe92c6f05348e31b8bab79718158135d556980c8c5bb7`。
3. 8 个 14K prompt/max_tokens=5000 请求的第一次 SSH 同时被主动终止；8/8 均由第二次
   取回成功，实际模型内容各 24,548 chars；每个远端 job invocation=1，全部响应 SHA
   与本地交付逐一相同。

结构化门禁 `durable_transport_gate.json` 为 PASS，SHA-256
`d05c65e52cdaacb229d29c9e5df7af19963720ead308df0bb202aec04e9d3dc9`；人读报告
`DURABLE_TRANSPORT_GATE.md` SHA-256
`71f4b9f36f65754d2dc2a65ffc7bb13517a448e83ccd465696a6209bd60359b3`。报告只读取 job id、
状态、byte count、SHA 与 invocation count，不读取请求/响应内容、benchmark、acceptance
或 reference。正式运行将使用新的空 job root 与独立 audit；`RWKV_READ_TIMEOUT=900` 只给
同一响应跨公网恢复留出时间，不增加或重试任何模型调用，模型/采样/并发/Controller 不变。
