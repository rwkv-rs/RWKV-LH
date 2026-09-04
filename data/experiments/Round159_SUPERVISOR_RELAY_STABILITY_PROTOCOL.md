# Round159：Supervisor Relay 强模型稳定性预注册

日期：2026-08-23

## 目的

在 Round158 Full90 完成后，对同一 OpenAI-compatible 中转站上的候选强模型做低调用量、
无重试的固定探测，区分模型/路由的原始稳定性、严格 JSON Schema 兼容性、延迟与用量。
本轮不测试 RWKV，不生成训练数据，也不在 Round158 运行期间发起 completion 请求，避免改变
Full90 的外部负载。

## 固定候选与请求

- `gpt-5.4`
- `gpt-5.4-2026-03-05`
- `gpt-5.5-2026-04-23`
- `gpt-5.6-terra`
- `gpt-5.6-sol`
- `claude-sonnet-4-6`
- 每个模型顺序执行 5 次，共 30 次物理请求；客户端不重试、模型间不并发。
- endpoint：当前 `.env` 中的 `SUPERVISOR_BASE_URL`；密钥不写入产物。
- OpenAI chat completions；`reasoning_effort=medium`、temperature=0、max_tokens=512。
- 固定严格 schema：返回 `probe_id`、按升序排列的三个整数和固定 verdict；每次 probe_id
  不同以避免把完全相同的请求当成缓存命中。

## 固定指标与选择规则

- raw HTTP success、HTTP 4xx/429/5xx、timeout/connection error。
- JSON body/choices/content 可解析率、strict schema 合规率、语义精确率。
- 每模型成功率、精确率、p50/p95 latency、prompt/completion/reasoning/total tokens。
- 进入真实 Planner/Reviewer canary 的稳定候选必须 5/5 HTTP 成功、5/5 schema 合规、
  5/5 语义精确；若多个模型满足，优先 p95 更低、total tokens 更少者。
- 该探测只选择传输候选，不代表 Planner/Reviewer 任务质量；胜出者仍必须在固定 canary
  上与 GPT-5.4 对照，不能直接替换正式配置。

## 数据记录

- 脚本：`temp/probe_round159_supervisor_relay_stability.py`，必须用绝对路径执行。
- 输出：`data/experiments/Round159_supervisor_relay_stability_20260823/results.json` 和
  `REPORT.md`。
- 记录脚本 SHA-256、候选、固定请求摘要、逐次状态/延迟/usage/输出摘要与生成时间；
  不记录 API key、Authorization header 或原始响应头。

