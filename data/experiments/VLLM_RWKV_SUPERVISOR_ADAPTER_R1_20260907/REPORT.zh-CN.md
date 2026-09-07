# VLLM_RWKV_SUPERVISOR_ADAPTER_R1_20260907

2026-09-07，WSL UbuntuRecovered；owner 授权扩大 Planner token 预算，并按 vllm-rwkv 请求格式接入。父提交 `57cee603`。本轮为传输、配置和验证整改，不是训练轮次。

## Agent 级结果

本轮没有启动 Agent 基准：Strict / completed / mutation / Agent 终止原因均无新增指标。连接探针和 mock 审计 fixture 不计成绩，不进入 StateTune 数据。历史 R2 A 为 Strict 0/12、completed 0/12、mutation 0，12 题 `strong_planner_unavailable`；旧结果保留原口径，B 未运行，没有有效双零比较。本轮修改生产源码后，未来两臂必须重新冻结并完整运行。

## 实际变更

- Planner 输出上限从 1,800 提高到 **8,192 tokens**，读取超时从 60 提高到 **240 秒**。Stage Checker 原有 2,400-token 输出预算保持不变。步骤和阶段数量不设固定上限，资源不足不能当作完成。
- Planner / Stage Checker 配置为同一现有 `rwkv7-g1j-13.3b-zero-state-capability-ctx16384`。本地 `29613/v1` 转发服务器 `18234/v1`；profile 为 `vllm-rwkv-native`，关闭缓存、fallback 为空。Selector 和其余角色配置、职责、State 机制不变。
- 新模块 `rwkv_lh/runtime/supervisor_vllm_rwkv.py` 只封装当前 Goal 两角色的原生 wire。角色请求仍由原来的 `GoalPlanRequest` / `GoalStageReviewRequest` 与生产唯一构造链产生；没有复制角色协议、增加角色或调用模型修补字段。
- 使用 `/completions`，prompt 为 `System✿{system}✿\nUser✿{payload}✿\nBot✿<think`，显式文本 stop `✿`、EOS 0、BOS、返回 token IDs。采样 temperature 0.1、top_p 1、top_k 0、presence/frequency 0、penalty_decay 0.996。每个请求显式 `zero` 和 64 个 0 的 State SHA，不读取 Executor sampling context 或 State handle。
- 不发送 `response_format` / `structured_outputs`。上一轮服务 traceback 已定位 JSON mode 在生成前导入缺失 `lmformatenforcer` 而 500；本轮使用部署已有的无 grammar 原生路径，没有安装依赖或重启服务。此方式不提供 grammar 强制 JSON 保证，字段正确性仍由模型与现有合同校验负责。
- 只接受唯一 completion、自然 `stop` 和以 `>` 继续实际 prefill 的原文；合回已发送的 `<think` 后使用既有严格 decoder。没有任意寻找 JSON 后缀、删字段、类型转换或把截断结果当成功。审计在解码前保存 attempt、完整原始响应、usage、原文与 SHA，保留 token IDs；坏 metadata 统一按传输协议错误处理，避免触发计划语义修复路径。
- 缓存键绑定 backend、URL、模型、实际 wire、预算、采样、stop 与 State 身份，避免不同后端或预算复用旧结果。

本地 `.env` / `.env.local` 与服务器两份对应配置已完成定向设置，均为 0600。服务器原来无这两个文件，本轮只创建 Planner 白名单键。六个独立 fresh production loader（两端各默认 `.env`、产品加载顺序、显式 `.env.local`）均通过；其他键逐项不变，原密钥未写入报告，临时 secret 副本已删除。见 `ENV_CONFIGURATION_APPLIED.json`。

## 连接实测与限制

| 检查 | 输入 / 输出 tokens | 结果 |
| --- | --- | --- |
| 生产 Planner 完整可见请求，单次生成 | 1,918 / 4,651 | HTTP 200，62.601 秒，自然 stop，JSON 语法通过；GoalPlanPatch 拒绝 |
| 原样 19 步 Stage Checker fixture | 15,067 / 预算 2,400 | 合计 17,467 超过 16,384 窗口；仅 tokenize，未生成 |
| 独立既有 1 步 Stage Checker fixture，单次生成 | 1,005 / 2,400 | HTTP 200，32.352 秒，重复思考后 length 截断，协议拒绝 |

Planner 请求来自已保存的可见生产请求，通过当前 dataclass 和原生产 builder 重建，正文一致；使用当前已取消五步要求的提示词。实际请求输入加最大输出为 10,110 tokens，容纳于部署窗口。原始结果产生 7 阶段 / 7 步，生产首先因额外顶层 `goal_digest` 拒绝。另行逐步观察发现 7/7 `success_evidence` 为字符串、S1 的 obligation_ids 为空、非 observe 步骤带 read_roots；这不是生产逐项错误枚举，也没有修补后重新判成功。见 `PRODUCTION_PLANNER_NATIVE_PROBE.json` 与 `PLANNER_NATIVE_RESPONSE_INSPECTION.json`。此探针执行时尚未追加最终 metadata 容器边界修复，其实际源码 SHA 已记录；后续修改未改变其请求、JSON parser 或计划合同，也未重跑或改写该结果。

19 步 fixture 来自原有 Controller 回归测试，有真实 Harness 读取、明确 mock accepted audits、完整 19 组引用和 8 条事实。最初 probe 在预检断言停止，`STAGE_CHECKER_NATIVE_CONNECTION_PROBE.json` 没有生成响应；随后独立 tokenize-only 检查把具体 15,067 输入和 17,467 总量记录在 `STAGE_CHECKER_NATIVE_CONTEXT_PREFLIGHT.json`。没有截断、降低输出预算或重复发起生成。

小 fixture 独立来自 `test_stateful_goal_loop_completes_only_after_rwkv_audit`，原测试完整执行并通过，包含真实 Harness 写入以及原有 mock 模型和审计；并非从大 fixture 裁剪。它仅用于接口连接。模型原文在关于文件 revision 的思考中重复，最终没有完整 JSON；2,400 个输出 token IDs 和原文完整保留在 `SMALL_STAGE_CHECKER_NATIVE_CONNECTION_PROBE.json`。

所以本轮已落实所请求的 Planner 预算和原生请求适配，但不能宣称 13.3B 的有效计划与阶段判定已经通过，更不能宣称达到全面基线启动条件。Planner 字段遵循、Stage Checker 思考重复/截断、较大阶段的物理上下文容量仍须分别处理；本轮未改变这些语义合同或其他角色预算以得到成功样本。

## 回归与根因证据

主适配红测 46 failed / 1 passed，修复后定向 47 passed。新增 metadata 值异常与 raw response 证据红测 4 failed；修复后包含原 Supervisor、角色配置与无步数上限回归的集合为 121 passed。独立审查又发现 usage 整体容器相邻缺口，3 failed → 3 passed。各日志保留原始结果，未覆盖红测。

最终 `.venv/bin/python -m pytest -q tests/`：**764 passed，62.43 秒，无跳过**。包含 Torch / State 和必需的浏览器验证，没有运行 `acceptance_tests/`。原生请求覆盖两个 Goal 角色、19 步完整输入、缺失/非法停止边界、token IDs、usage 容器和值、环境别名冲突、采样/State 隔离及缓存身份。`FINAL_CODE_REVIEW.zh-CN.md` 另行审查全部代码差异及失败证据边界。源码与部署 formatter 的字节/token 对齐、BOS、Unicode/控制输入、正负边界见 `RAW_COMPLETION_WIRE_AUDIT.zh-CN.md`；不把单测和源代码审计当作模型能力成功。

## 上传、记录与后续

生产源码、测试、README、HANDOFF、规范和 `.env.example` 共 8 文件已由本地 rsync 上传，并在服务器逐文件核对 SHA。见 `FINAL_UPLOAD_MANIFEST.json` / `FINAL_UPLOAD_VERIFIED.json`；全程没有服务器 Git 命令，没有更改模型权重、engine 文件、其他 GPU 服务或训练数据。Git 仅在本地使用，按本轮 id 提交，GitHub push 留给 owner。

本轮没有读取 Holdout 内容、修改历史确认集评分、创建角色 datasets 或启动训练。后续需先处理上述模型输出与容量限制，再登记新的完整两遍 zero-state 比较；不续接旧 R2 B，也不把连接 fixture 作为训练来源。

所有本轮临时脚本以 `.py.txt` 快照保留，正式代码不依赖 temp；完整工件清单在 `SHA256SUMS`，本报告与主要结论文件的 SHA 由该清单固定。
