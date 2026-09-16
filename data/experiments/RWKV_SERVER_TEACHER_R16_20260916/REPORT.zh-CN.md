# R16：服务器内完整纠错链路与工程修复

## 当前任务结果

R15 已因第三题 HTTP ReadTimeout 停止，不再是“20题运行中”：前两题产物均不通过，第一题12次调用耗尽，第二题仅提交后续计划；第三题请求中断，17题未运行。原始评分、候选与 trace 保持不变。R15 第一题确实写入并执行过测试，不能把 check_command 误说成只生成检查计划。

R16 同20题重新冻结，所有调度、隔离工作区、模型调用、工具执行、外部代码测试与原始记录均在服务器 rwkv-82。服务器 unit `rwkv-lh-server-teacher-r16.service` 已启动。首个快照：2题提交、0产物通过、0修改；第3题生成中。两题输出均停留在计划说明，没有交付 solution.py，不能称为合格纠正。完整20题、语义验收未完成；不报告项目 Strict，不计入训练数据。

## 已确认的工程问题

1. **执行位置**：R15 的模型在服务器，调度与测试在 WSL，依赖 SSH 模型端口转发。R16 整条链路已迁服务器，直接请求 `127.0.0.1:18243`。本地 SSH/rsync 只作部署控制和取回证据。
2. **HTTP超时与任务预算不一致**：非流式请求固定240秒，而输出上限8192token、实测约8token/s、单题1200秒。第三题服务持续解码时客户端先断开。新增 `DeadlineStrongCompletion` 按剩余任务时间设置连接/读取超时，不自动重试；已有任务总时限仍生效。原始响应和精确输入/输出token IDs继续核验记录。回归 RED→GREEN 已留存；不声称解决网络断线后恢复部分输出。
3. **服务器沙箱配置缺失**：真实 bwrap 操作失败，内核日志明确 AppArmor 的 `unprivileged_userns` 拒绝 setpcap/net_admin。新增 `/etc/apparmor.d/rwkv-lh-bwrap` 仅绑定 `/usr/bin/bwrap`，按 Ubuntu 专用 userns profile 方式配置；未关闭全局 AppArmor/userns限制。配置SHA `a236fc2628d57f07e5e06845ab2ef31a10b91cffcf34995d4278fc87bcbfceab`。
4. **系统Python虚拟环境链接映射遗漏**：服务器venv的python链接到 `/usr/bin/python3.12`，Harness此前保留宿主 `/home/.../venv/bin/python`，隔离后不可见。通用修复将venv入口映射到只读挂载 `/opt/rwkv-lh-venv`，其他系统解释器别名解析为实际系统路径。新增失败→通过回归，并真实验证服务器stdin、工作区写入、私有文件不可见。

外部stdio真实执行也已验证正确输出通过、错误输出拒绝、死循环超时（SERVER_STDIO.txt）；这是工程测试夹具，不计采集/训练数据。

沙箱完整验证结果见 `SERVER_SANDBOX_FIXED.txt`。前两次失败分别保存在 `SERVER_SANDBOX.txt` 与 `SERVER_SANDBOX_GREEN.txt`（后者是中间候选命名，内容实际为失败，未覆盖）。`SERVER_PROBE.txt`只证明原始输入逐字节到达模型客户端；首题原工作区无 solution.py，其baseline是 missing_submission，不代表该probe执行过Python。实际执行证明以 SERVER_SANDBOX_FIXED 为准。

## 冻结与可比性

- 相同R15选择20题、源输入、快照、私有stdio验收、12调用/1200秒/8192输出token、temperature1/top_p0.95/top_k40。
- Qwen3-Coder-Next-FP8固定模型revision `da6e2ed27304dd39abadd9c82ef50e8de67bdd4c`；继续用既有GPU0+3服务，不启动RWKV训练。
- 以原真实生成边界的完整输入文字初始化教师新checkpoint，仅历史文本迁移，不宣称RWKV原生State张量可用于Qwen。后续执行仍用既有生产Controller/协议/输入构造，无提示词补丁、参数代填、答案改写。
- 源材料和私有验收独立于可见workspace；原始绑定保留，新路径仅在部署清单中映射。
- Python由本地3.13转为服务器3.12；部署位置、HTTP超时、沙箱路径同时改变，本轮只能验证工程部署与真实纠错，不是某单项模型能力收益消融。
- 完整文件manifest本地生成并上传，服务器启动核对1055文件；manifest SHA `4afc999ac6be37456fa1856fddf57e66efd4bb549eee6dca884f498cdbc62bba`。服务器不调用Git。
- 20题完成后待语义审核；基础设施错误停发，任务/协议预算失败原样保留，不自动补答案。未新增datasets版本，训练准入0。

## 尚未解决与下一步

前两题仍只总结/规划后提交，说明工程运行正常不等于教师完成任务。原始文本整体放入system、user为空JSON的输入封装是否影响执行，目前只是有依据的假设；R16冻结运行中不修改。20题后逐条审计“实际写入/测试/产物/最终陈述”，再单独冻结教师输入组织对照，避免把提示改动与换模型混成一个收益。

Qwen3.8确有官方开放权重，候选可从27B/27B-FP8开始，但本轮未下载或切换；任何替换须独立绑定权重、推理配置和同组验收，不能把型号名称当作纠错合格证据。
官方依据：[Qwen3.8仓库](https://github.com/QwenLM/Qwen3.8/blob/main/README.md)、[Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B)。
AppArmor依据：[Ubuntu用户命名空间说明](https://ubuntu.com/blog/ubuntu-23-10-restricted-unprivileged-user-namespaces)。

## 运维查看

服务器目录 `/home/chase/GitHub/RWKV-LH-server-teacher-r16-20260916/`：

- `outputs/STATUS.json`：队列进度/中断原因。
- `outputs/runs/<ID>/DELIVERY.json`：原始提交与独立产物验收，语义状态单列。
- `outputs/runs/<ID>/execution/`：真实生成输入/输出、token、工具与checkpoint记录。
- `outputs/HOST.json`：执行主机、Python、端点与manifest身份。

服务器用户systemd查看前设置 `XDG_RUNTIME_DIR=/run/user/1001`、`DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1001/bus`；然后 `systemctl --user status rwkv-lh-server-teacher-r16.service`。不依赖本地端口转发或本地前台进程。模型unit仍为 `rwkv-lh-teacher-r15.service`，其名字是模型部署身份，不代表R15评测试验仍在运行。

原owner五处修改逐文件SHA不变，未包含在本轮提交中。首次完整回归在修复沙箱代码后主动中断，日志保留；最终完整回归 FULL_TESTS_FINAL.txt：1890 passed，0 skipped，359.71秒。已返回9次生成的精确token核验通过，110344输入/2663输出token；这仅是当前快照，不是20题最终费用。

本轮证据逐文件SHA见 `EVIDENCE_SHA256.json`；本地工程测试使用WSL，服务器执行是owner本轮明确要求的纠错部署。
