# STRONG_UPSTREAM_STABILITY_R1_20260907

2026-09-07，WSL UbuntuRecovered。owner 要求复查强模型，稳定后直接运行。结论：**当前 next-token.cc / gpt-5.6-sol 的完整 Planner 生成仍返回 HTTP 500，未达到运行门槛，因此没有启动新的双零基线。**

## Agent 级结果

本轮未启动 Agent 评测，没有新增 Strict / completed / mutation / Agent 终止原因数字，也没有新的角色训练数据。此前 R2 A 的原始结果、确认口径及未启动的 B 臂保持原样。没有新建 R3 执行目录、读取 Holdout 或启动训练。

## 实际请求与稳定性判定

owner 本轮提供的凭据仅保存于本地忽略追踪的 `.env.strong.local`，权限 0600；现有生产 `.env` / `.env.local` 未切换。诊断采用同一 `gpt-5.6-sol` 作为 Planner / Stage Checker，当前生产 `openai-compatible` 路由两者均为 `/chat/completions` + JSON mode；没有临时改成 Responses 或调整 parser。

运行前已冻结 `STABILITY_PREREGISTRATION.json`：当前代码与完整请求 SHA、模型、Planner 8,192 tokens / Stage Checker 2,400 tokens、读取超时 240 秒、单次 HTTP 尝试、无缓存、fallback 或语义补救。固定顺序为 API01 初始、API02 初始、小阶段、19 步完整阶段、API01 真实 repair continuation，然后同序再一遍，共最多 10 请求。任何首次失败即停止，剩余未运行；合法 Stage `repair` 不算格式失败。所有 10 次自然结束、JSON 和原合同均通过才满足本次有限窗口开跑门槛，不声称长期 SLA。

Planner 材料来自已有可见生产 trace，使用当前唯一 `GoalPlanRequest` 和生产 builder 重建，沿用已取消步数上限的当前提示词。Stage 材料是已标注 mock 审计的现有 Controller fixture，仅用于连接检查。没有裁剪或手工发明协议输入。

| 检查 | 结果 |
| --- | --- |
| 认证后 `/v1/models` | 成功；gpt-5.6-sol 存在；耗时 7,318.3 ms |
| 第 1 条完整 Planner 初始请求 | HTTP 500，32.8 秒，`new_api_error` / `do_request_failed` |
| 有效模型 JSON / 计划合同 | 未收到模型输出，未进入计划合同校验 |
| 固定矩阵 | 0 通过 / 1 失败 / 9 未运行，gate=false |

本次请求 ID：`202609070625338139019158268d9d667ty3WNA`。完整原始错误与响应头 ID 保存在 `PROBE_01_initial_api01.json`。模型目录能读并不证明生成可用；同类错误已在先前上游诊断出现，本次仍不能根据客户端错误体确定提供方的内部渠道、超时或路由根因。未发送对外消息，也没有以其他模型或修改请求替换失败样本。

## 运行环境与下一轮准备

RWKV 两服务保持 active/running，PID 1486276 / 1476735 不变；远端端口 18234 / 18239、本地 SSH 转发 29613 / 29621 正常。两套完整 engine 清单含 6,395 / 6,386 文件，文件集合、逐文件 SHA 和清单自身 SHA 均匹配；两模型 safetensors 实际 SHA 完整重算匹配。Selector decoder / zero 身份、13B native State 能力、本地与远端全部当前生产 Python 源码均一致。其他 GPU 服务未调整。此处是运行时就绪证据，不能代替失败的强模型生成检查；见 `RUNTIME_READINESS.zh-CN.md`。

R3 离线准备审计确认 runner、评分器、题集及 collector 的 7 项 SHA 与 R2 一致，12 题顺序不变，可以保留原评分。执行前仍需生成当前配置、源码与比较身份的新冻结；旧驱动固定 R2 目录/身份，不能继续旧 B 或把失败题重跑拼成一臂。具体审计见 `R3_READINESS_AUDIT.zh-CN.md`。该子审计中凭据 pending 是其完成时状态；本轮随后已收到并实际使用凭据，最新阻塞是上述 HTTP 500。

本轮未修改 `rwkv_lh/`、`tests/`、runner、评分器或模型服务，也没有重评分旧输出。前轮同生产/测试代码的全量结果为 764 passed、62.43 秒、无跳过（`VLLM_RWKV_SUPERVISOR_ADAPTER_R1_20260907/FULL_TESTS.log`）；本轮不重复宣称新单测执行，以文件指纹核对保持一致。新增内容是独立检查脚本、原始证据与 README / HANDOFF 最新状态。

继续运行的条件仍是强模型完整请求通过同样的稳定性与合同检查；若上游恢复，可使用已保存凭据执行新的、单独登记的复测。没有创建定时任务，本轮也没有在不稳定状态下启动全面运行。

## 证据与提交

冻结登记 SHA-256：`aff1d396beed52e8c97458a6cf56af32f01621e304267438c094a4176a510e54`。

首发失败证据 SHA-256：`f3f81e020ae8ec1d74b34a80e8735951b43af33d4196461e1651d54a9adc639a`。

预检代码审查 SHA-256：`991996a0f667cf18228ea05ac12c95a5af680e01c64bb8b59f3e2443ed0fe195`。

过程脚本保留为 `.py.txt` 快照，工件与本报告 SHA 见 `SHA256SUMS`。按本轮 id 本地提交；文档及证据仅从本地上传服务器并核对哈希，服务器未执行任何 Git，凭据不上传。owner 负责 GitHub push。
