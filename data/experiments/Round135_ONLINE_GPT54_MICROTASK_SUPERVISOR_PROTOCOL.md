# Round135 GPT-5.4 在线微任务 Planner/Reviewer 协议

日期：2026-08-22

## 1. 要验证的架构

Round135 不复用 Round134 的“一次静态 Plan + 只审 Final”。GPT-5.4 在任务执行期间持续在线：

1. 初始读取用户原文、约束与公开 workspace manifest，只下发一个可观察验收的微任务。
2. RWKV 是唯一动作主体，自行选择并执行 direct Harness operations；独立 case 由 worker pool 并发执行。
3. 每个微任务允许 RWKV 连续执行最多 6 个底层工具动作。达到波次边界、出现连续零进展重复或提交 Final 后，GPT-5.4 在一次调用中验收这一波并只下发下一个微任务；如果未满足则给出聚焦修正。
4. RWKV 过早提交 `final_answer` 时，GPT-5.4 在线退回并给出下一微任务；只有公开动作、artifact 和 workspace 证据支持目标时，才接受该次 RWKV 原文 Final。
5. GPT-5.4 不调用工具、不构造 Harness 调用、不写业务文件、不生成或改写最终答案、不可见 hidden acceptance。

因此，每个 committed directive 必须对应 `initial`、一个包含 1--6 个新 actions 的波次，或一个新的 RWKV Final candidate；不允许在同一 observation 波次上重复调用多个 planner/reviewer 模块。GPT 是低频控制面，大量工具调用和业务执行都留在可并发扩展的 RWKV 执行面。

## 2. 固定实现与预算

- Worker：本地 `.env` 登记的 `rwkv7-g1i-13.3b-20260805-ctx16384` forward，prompt replay，temperature 0.05，full tool disclosure。
- Supervisor：OpenAI-compatible `gpt-5.4`，temperature 0.1，strict JSON schema。
- 每个 Supervisor 输出：对上一 outcome 的 `initial/satisfied/needs_correction` 评语，以及 `continue/accept_final`；`continue` 时必须恰好一个微任务 objective、completion checks 和 constraints。
- 每题最多 64 个 committed online directives（含 initial 与 Final review），超过即 fail-closed interrupt。
- 正常 review cadence 固定为每 6 个 RWKV actions；若同一 action fingerprint 连续 2 次且 workspace digest 均不变，则提前触发一次在线 review，防止等满波次后继续陷入吸引子。
- Controller 每题 max transitions 200；case workspace 彼此隔离，canary concurrency 3，Full90 concurrency 6。
- Supervisor 输入最多保留最近 32 个 actions；单个 action output 最多 2,000 字符；workspace manifest 最多 256 entries / 1,800 tokens。
- API 密钥只从 ignored `.env`/环境读取，报告只记录模型、digest、latency、usage，不记录 key 或原始 headers。
- 评价仍使用固定 RWKV-E2E-90 isolated verifier；不更改 hidden checks、Strict 定义、相似度或阈值。

## 3. 固定 canary

在任何 Full90 前固定运行：

- E2E-B01：基本写入、读取验证和正确完成边界。
- E2E-M11：多对象 artifact 已正确但历史上陷入重复 `read_json`，检查在线验收能否进入 Final。
- E2E-H17：历史上 200 次相同 `read_file`、0 workspace change，检查在线微任务能否打破首次落盘前吸引子。

三题以 concurrency 3 同时运行。输出目录固定命名 `Round135_online_gpt54_microtask_canary_B01_M11_H17_20260822`；若因实现 bug 产生无效运行，修复后只能用带 `rN` 的新目录并保留旧目录和原因。

## 4. 预注册 canary gate

只有以下条件全部满足才进入 Full90：

1. 3/3 运行有效，无 supervisor transport/protocol failure、无 verifier 隔离失败、无 running 残留。
2. B01 与 M11 均为 Strict TP。
3. H17 至少发生一次 workspace digest change，且同一零信息 action fingerprint 在已收到在线修正后不得再连续出现 5 次；H17 是否最终 Strict pass 单独报告，不作为放宽前两题要求的替代项。
4. 审计证明每个非初始 directive 都只验收一个新的 1--6 action 波次或 Final candidate；GPT action count 为 0；delivered Final 与被接受的 RWKV `final_answer.text` 字节一致。
5. 三题合计 protocol rejection 不超过 6，且没有题耗尽 64-directive budget。

任一 gate 失败：停止 Full90，做因果分析；不得改 case、门槛或评价口径后将同轮标为通过。

## 5. Full90 条件与晋级门槛

仅 canary gate 全通过后，使用同一代码、行为参数、64-directive 上限和 fixed RWKV-E2E-90 运行 Full90；调度并发固定为 6 个隔离 case workers。相对 R126 official（TP36 / FP30 / FN0 / OTHER24）的晋级门槛固定为：

- 有效 90/90，0 running；
- Strict TP > 36；
- FP <= 24；
- FN <= 1；
- 5 个 byte-precision cases 全部通过；
- Basic / Medium / Hard / Long-horizon 分层无系统性 completion collapse；
- 不存在 credential、hidden acceptance 或 supervisor action 泄漏。

未满足则不替换 canonical baseline，但保留逐步 directive/action trace 作为后续 state-tuning 候选种子；正负标签仍由 frozen verifier 和 workspace evidence 决定。

## 6. 无效首轮登记

目录 `Round135_online_gpt54_microtask_canary_B01_M11_H17_20260822` 保留为无效首轮：实际
`model_session_bootstrapped.tool_disclosure_mode=progressive`，与第 2 节冻结的 full disclosure
不一致。三题均达到 12 次 protocol rejection；B01 artifact 已通过 isolated verifier，但被接口
选择协议阻断完成。该轮不计入 canary gate，也不用于判断在线微任务架构。修正仅限把运行时
disclosure 恢复为预注册的 `full`，行为代码、case、预算和门槛不变；有效重跑使用 `r2` 新目录。
为避免父 shell 的 progressive 环境变量覆盖 ignored `.env`，r2 必须显式传入 runner 参数
`--tool-disclosure-mode full`；`RUN_PROTOCOL.json` 和每题 model trace 都必须记录 full。
