# 当前交接

2026-09-11 owner 将目标提高为 **至少500条有效 Selector train 样本**，固定3dev/2confirmation另保留。[Selector500 预注册与启动](../data/experiments/SELECTOR_500_CAMPAIGN_R1_20260911/REPORT.zh-CN.md)：98个公开开发任务已固定队列，首批12题已开始，原数据仍19train/5评测，未声称500达成。首题Strict0/1、completed0/1、mutation1、动作3，因重复成功动作预算耗尽停止，外部文件检查通过但无Final；3自动候选/6待审仅为管线探针，不计最终新增。有效训练样本与独立决策边界分别报告，目标边界至少167。保持原去重和五个评测anchor；Selector训练及固定回归合格后才转Executor。

已按新授权push至3ae1efcc；本轮推理源码也冻结在该提交的隔离工作树，部署根`/home/chase/GitHub/RWKV-LH-selector-500-runtime-r1-20260911`，项目SHA`524a195270d8d10062e87a17a7c0c5dba36ceae3c83e3413ca34c85a01def0c5`，engine SHA`9fdfd8e8b11f6c6de3df30ae9e36088765cf9780831595b49150d4e95375b32a`；132/6393文件核验及服务健康通过，无服务器Git。1479项测试对应本轮冻结代码，不覆盖主工作区正在进行的另一轮修改。以下24/30的数量门描述是较早历史，当前按500train目标执行，训练未启动。

更新日期：2026-09-11。[轮次 A 与当前数据门](../data/experiments/SELECTOR_EQUIVALENCE_RENEWAL_R3_20260911/REPORT.zh-CN.md)：**Strict 0/4、completed 0/4、mutation 0、动作 6**；两题无进展、两题协议拒绝。NEW-DIAG-02 三次 check_command 成功取得预期失败诊断，绑定 execute；未修复或交付项目。A 的采集 KEEP 达到，B 不启动，Executor 仍为 1800。

原指定 162e60ee/c6b46d01 已 push。A 提交 67f1edd4，数据冻结修复 5edcccde，完整回归 **1479 passed、0 failed、0 skipped**。新 42 条待审全部处置（34 接受、8 拒绝）；在双签冻结 5edcccde 上精确重放 22 来源的 256 条，按原政策保留 24 条（19/3/2），**status=valid、execute=3**，原五个评测 anchor 不变，全部 24 条 normalize 通过。真实重放与政策候选逐字节一致。共享工作区随后新增的 harness.py / supervisor_openai.py 修改未被本次签名和回归覆盖；首次组合重放的 SHA 拒绝与隔离验证分别留证，他人改动保留。

**首训仍未启动：有效 24 条/9 个独立边界低于预注册 30/10；freeze、smoke、optimizer steps 均为 0，没有新正式数据集版本。** 下一步补登记独立生产采集，保持原去重和评测口径，净增至少 6 条与 1 个边界后再推进冻结/首训。首次 freeze 不虚构 prior。当前部署根 `/home/chase/GitHub/RWKV-LH-execute-coverage-a-20260911`，项目 manifest `02e144adeaa4b3ecee0413b4ef94ef6bc04e415b751fa12baba0ff28798f7211`，engine `7aaffd9167c63c02703bde19c1d36d0ea9bdacdd325faa8800ee44cde7633daf`；服务器未用 Git。新本地数据冻结修复不冒充已部署推理源码。

本轮重放证据清单 SHA-256：`7f7c344f78aed9047ba4945ec509563e580f9d0f5d76274a35da29123dd2543b`。后续本地提交按 AGENTS 由 owner push。以下较早结果保留为历史，以本段为当前状态。

**当前能力：已证明在给定工作区写入代码文件，尚未证明可靠自主创建并交付项目。** 最新三轮独立Agent结果如下，不合并分母：

| 轮次 | Strict | completed | mutation | 动作 | 终止原因 |
|---|---:|---:|---:|---:|---|
| 新命令路径采集 | 0/4 | 0/4 | 0 | 13 | identical_success_budget_exhausted×3；protocol_rejection_budget_exhausted×1 |
| baseline1800 | 0/2 | 0/2 | 0 | 4 | identical_success_budget_exhausted×1；strong_planner_unavailable×1 |
| candidate3600 | 0/2 | 0/2 | 0 | 2 | goal_audit_protocol_rejection_budget_exhausted×1；protocol_rejection_budget_exhausted×1 |

最新全流程状态见[六项继续执行结果](../data/experiments/SELECTOR_GATE_CONTINUATION_R1_20260910/REPORT.zh-CN.md)。指定f34e4964与21c0cf45已push；当前部署根`/home/chase/GitHub/RWKV-LH-audit-fanout-r1-20260910`，项目manifest SHA `f7569e52896794cda754bce231ea9d449b5013516fd2dfc890064f0099343926`，engine SHA `5c229e24e9158a5d66df8c67d508c2934044766f49dbea39f4a89d64080c1d74`，服务完整文件身份与健康通过，服务器无Git。生产源码保持21c0cf45，完整回归1455 passed/0failed/0skipped。

[重签](../data/experiments/SELECTOR_WAIVER_RENEWAL_R1_20260910/REPORT.zh-CN.md)已双AI accept，waiver `f53186ecfca2f97126b132f41b1bc37bdef46e77ce91b3cde4a68385ef0a3aaa`恢复原14来源60候选、126待审行。[旧126复核](../data/experiments/SELECTOR_SEMANTIC_REVIEW_R1_20260910/REPORT.zh-CN.md)和[新43复核](../data/experiments/SELECTOR_FRESH_SEMANTIC_REVIEW_R1_20260910/REPORT.zh-CN.md)均已完成处置：136共同接受、33拒绝，待审0。按[预注册去重](../data/experiments/SELECTOR_SIMILARITY_POLICY_R1_20260910/REPORT.zh-CN.md)，210→20（15train/3dev/2confirmation），原5anchor不变，超相似对0/81。

[新四题采集](../data/experiments/COMMAND_PATH_COLLECTION_R1_20260910/REPORT.zh-CN.md)仍check/run=0、execute=0，命令路径覆盖目标未达到。[预算试验](../data/experiments/EXECUTOR_OUTPUT_BUDGET_R1_20260910/REPORT.zh-CN.md)为NO_KEEP，生产Executor默认1800不变。[最终训练预检R2](../data/experiments/SELECTOR_TRAINING_PREFLIGHT_R2_20260910/REPORT.zh-CN.md)纠正R1中间/最终行相同的文字，已对实际最终20条全部normalize通过。候选仍INVALID：缺execute覆盖，freeze_dataset又未接通waiver/筛选再现。首轮尚未登记、optimizer steps=0；首次freeze不要求虚构prior，已有regression复用才要求三重pin。owner授权有效，低分不是禁训门；下一步补真实execute来源与冻结接口，再按数据门登记smoke/首训。

以下R2及更早段落是冻结历史，旧文中的“尚未部署”“待重签”“仅授权waiver”及旧源码首错缺陷状态以以上最新证据为准。后续本地记录提交按AGENTS由owner push。

2026-09-10 [充值后执行复测R2](../data/experiments/EXECUTION_EVIDENCE_REVALIDATION_R2_20260910/REPORT.zh-CN.md) 已全部完成：**Strict 0/7、completed 0/7、mutation 2、动作18**；5题无进展、1题Executor协议拒绝、1题Step Auditor协议拒绝。与R1已生成八题的同源码关联视图为 **Strict 0/15、completed 0/15、mutation 6、动作46**（10题无进展、4题Executor协议拒绝、1题Step Auditor协议拒绝），不是一次性新15题运行。充值后Supervisor请求失败0、输出中断0，R2新增60次交接全部核验，关联视图160次；Finalizer/Final Auditor仍未到达。生产源码冻结b3e89de6不变，完整回归1447 passed、0 failed、0 skipped，optimizer steps=0。

**KEEP未通过。** 新确认 [Native首错审计接线缺陷](../data/experiments/EXECUTION_EVIDENCE_REVALIDATION_R2_20260910/NATIVE_AUDIT_WIRING_FINDING.zh-CN.md)：实际产品/benchmark会话工厂未将audit_hook交给Native client，四角色离线POST/404/404/POST均成功恢复却丢失首错事件。故不能由native_first_errors=0声称无首错丢失；此项未修复，后续独立工程轮需先失败后通过的工厂集成回归，不能用训练掩盖。Executor另有18次length（FULL-02十二次、WEB-02六次），与Supervisor中断分开。WEB-02两次写入但没有运行check/run命令，历史命令路径仍未在本轮Agent覆盖。最新 [正式架构复核](../data/experiments/EXECUTION_EVIDENCE_REVALIDATION_R2_20260910/ARCHITECTURE_FIT_REVIEW.zh-CN.md) 保留五角色作为工作架构，不宣告能力通过；三项流程单变量轮仍排首轮StateTune之后。R2报告SHA `88a4790423c6546d31ed34785564b68f58f2bb03dda1ba526b270f4c78d6391d`，证据清单SHA `b0b8209e8b25edc517529dcb4a4f354197f6020bab045fb758beabf86dc3c69f`。

原 [执行修复复测R1](../data/experiments/EXECUTION_EVIDENCE_REVALIDATION_R1_20260910/REPORT.zh-CN.md) 的 **Strict 0/15、completed 0/15、mutation 4、动作28** 与七题HTTP402原始记录全部保留。R2复核三个R1证据清单下303个文件SHA均未变，R1不改分、不续写。R1关于Native零日志的过强解释以本轮接线探针更正为准。Owner负责push。

本轮两个独立AI reviewer已获owner明确授权，仅用于waiver技术复核。原全量draft未获一致批准；新14来源、仅Selector的精确scope已双签并正式提取，排除受旧check执行语义影响的RP-WEB-02。恢复60自动候选、126待复核，原9边界/27行完整保留；候选仍INVALID（execute=0，281对跨切分比较有101对超阈值），没有借waiver批准语义标签或训练。详见 [waiver结果](../data/experiments/EXECUTION_EVIDENCE_REVALIDATION_R1_20260910/WAIVER_RESULT.md)。R2不扩大此waiver。以下较早交接为历史背景，以以上最新段落和R2证据为当前状态；旧文“首错修复全部落地”和“待充值/AI授权未答复”均已被新证据更新。

更新日期：2026-09-10。最新完整开发采集 [REALPROJECT 官方 R3](../data/experiments/REALPROJECT_OFFICIAL_COLLECTION_R3_20260910/REPORT.zh-CN.md)：**Strict 0/12、completed 0/12、mutation 0、动作 43**；12 题均取得初始计划。7 题无进展、2 题参数/工具协议拒绝、1 题 Native create 未确认、1 题 Step Auditor 协议拒绝、1 题命令执行失败。全部已返回的 117 次角色交接通过输入字节及完整 token 核验；不是全链路语义验收通过。optimizer steps 仍为 **0**。

此前第三方网关 [REALPROJECT R1](../data/experiments/REALPROJECT_HANDOFF_COLLECTION_R1_20260910/REPORT.zh-CN.md) 为 Strict 0/12、completed 0/12、mutation 0、动作 0，10 题 HTTP 500、2 题 Native 边界失败。官方 [UltraData R5](../data/experiments/ULTRADATA_OFFICIAL_COLLECTION_R5_20260910/REPORT.zh-CN.md) 为 Strict 0/3、completed 0/3、mutation 0、动作 1，2 题默认 high 思考耗尽输出。这些历史结果保持原评分；旧 REALPROJECT 官方 R2 只预备、从未生成，已关闭。

最新 [UltraData 官方 R6](../data/experiments/ULTRADATA_OFFICIAL_COLLECTION_R6_20260910/REPORT.zh-CN.md)：**Strict 0/3、completed 0/3、mutation 3、动作 6**；三题均拿到计划并写入文件，0 个 Strong 请求失败，29/29 角色交接完整核验。终止于无进展、工具/参数拒绝和 Step Auditor 协议错误。3+12 题已全部结束，均使用冻结源码 e7c455b6。

## 当前整改与验证状态

[执行证据与传输修复 R1](../data/experiments/EXECUTION_EVIDENCE_REPAIR_R1_20260910/REPORT.zh-CN.md)：**审计确认的 E1–E4 全部修复，E6 兼容准入通道落地，完整回归 1447 passed、0 failed**。R1 准入器新增双人复核等价豁免映射表（vocab 与角色协议不可豁免，checkpoint 字节重建等语义防线不受影响，无 waiver 行为逐字节不变）；R2 check_command 改为 bwrap tmp-overlay 临时工作区（写入不保留）、失败命令写范围 fail-closed、超时保留部分输出（对照探针三项全部达预期）；R3 Native 首错保留审计事件、收据 404 语义化为"证明未执行"并有界重发（真 unknown 仍绝不重发）、连接层 connect-only 重试 + mutation `Connection: close`、benchmark 增 `--native-transport-resume-attempts`（不改评分）；R4 SSE 容忍 usage 尾帧、length 有界重试、thinking 下 review/directive 预算 2800/2400。删除三个确认无引用的死函数；全仓死代码候选清单与 E5 持续会话设计+可行性探针一并归档。**遗留门（owner）**：重跑 15 题评测；`EQUIVALENCE_WAIVER_DRAFT.json`（6 文件，decision=draft）双人复核改 accept 后用 `--equivalence-waiver` 验证旧 trace 恢复准入。

[剩余问题审计 R1](../data/experiments/ENGINEERING_REMAINING_AUDIT_R1_20260910/REPORT.zh-CN.md)：当前确认 4 项代码缺陷（check_command 可写、失败命令漏写范围检查、超时丢部分输出、Native 恢复丢首次错误）、2 项设计/能力缺口（持续进程会话、修复后 trace 兼容准入），另有 1 项 Native create 未知结果事故。该数量是已证实事项下限，不是全仓库错误总数。真实隔离 Harness 与离线客户端探针已留证；本轮未修生产代码、未重跑 Agent 或训练。97 次 Executor + 49 次 Step Auditor 输入交接已核验，不能扩称全部角色能力通过；最终两个角色仍未到达。

[命令入口整改 R1](../data/experiments/COMMAND_ENTRYPOINT_REPAIR_R1_20260910/REPORT.zh-CN.md)：**1432 passed、0 skipped**，修正后的行为测试在旧 Harness 上 14 failed / 4 passed。项目原生可执行文件不再被当成 Python 脚本，console script 保留解释器参数；原 WEB-02 命令在独立 bubblewrap 中退出 0。修改在本地命令执行层，推理服务器上传源码和 manifest 身份仍为下述已验证版本。本轮无新 Agent 成绩，Native create 404 的最初传输原因仍未查明。

[官方请求与 trace 整改 R1](../data/experiments/OFFICIAL_PLANNER_TRACE_REPAIR_R1_20260910/REPORT.zh-CN.md)：**1414 passed、0 skipped**；同一 R5 真实交接 14/14 输入字节一致。扩展注册表覆盖到重建和标签校验，输出耗尽在解析前保留停止原因/用量。当前 Planner 与 Stage Checker 均显式 low 思考；新 3+12 题全部取得计划，仍有计划补丁语义拒绝。最终 2.9B 8 项全词表精确对齐、至 16384 token 反向通过。后续命令入口整改已处理新采集发现的二进制误当脚本问题；另一次 Native create 未确认仍保留未查明状态。

[交接结构整改 R1](../data/experiments/ROLE_CHAIN_ROOT_REPAIR_R1_20260910/REPORT.zh-CN.md) 已提交 `82319f95`：原始需求贯穿 Executor / Step Auditor，参数拒绝由同一步的 Selector / Executor 接收，路径资格和执行权限共用参数合同，逻辑交接及事实提交与 Native 缓存物化分开。完整回归 1321 passed、0 skipped；随后真实采集暴露新的数值边界缺陷，因此不能将工程通过称作完整交接验收通过。

两道实际失败题中，首次生成后服务器 processed_token_count + 1 比返回 token 的完整历史长度多 2；后续 append 原样继承偏差。错误起点是把终止输出时捕获的 worker 当前 State 当作该输出对应的 State。原始数值证据见 REALPROJECT R1 `NATIVE_TOKEN_EVIDENCE_FAILURE.json`；该轮报告 SHA-256 `6bbd6c78a7a2333fa09482f68857834a73fa45b4c73aac4910186b65cfbe1cc4`。

当前 [数值边界整改 R2](../data/experiments/NATIVE_BOUNDARY_REPAIR_R2_20260910/REGISTRATION.json)：候选缓存仅从已核验父 State 与实际返回 token 物化后发布，采样工作区不直接作为交接 State；单次角色采样与确定性缓存工作分别计量。Native / Selector 共用 State profile loader；Supervisor 在协议解析前保留原始 SSE 行，缺少生成停止原因不再伪造 stop。完整测试 **1341 passed、0 skipped、231.41 秒**；新源码已上传并验证完整项目 / engine 清单，真实 GPU 停止符、重试与重启验证已通过，State 张量与精确前缀最大绝对差为 0。R2 已封存，尚无新 Agent 成绩。

[StateTune 入口整合 R2](../data/experiments/STATETUNE_DRIVER_INTEGRATION_R2_20260910/REPORT.zh-CN.md) 已接通生产 trace 数据冻结、State-only 优化器登记/导出、Selector 固定回归比较。专项 50 passed，完整回归 **1390 passed、0 skipped、225.13 秒**；源码已冻结上传。服务器系统包更新使 12 个共享库与旧清单不同；已核对 dpkg 更新及文件验证，数值兼容检查按新依赖重新登记，首次拒绝与复验分别留证；8 项全词表比较精确相等，1/17/128/16384 反向均通过。实际角色优化器尚未运行。

## 唯一架构与服务配置

产品入口 `rwkv-stateful-goal-loop.v7`，保持五个训练角色：Selector → Executor → Step Auditor → Finalizer → Final Auditor。各角色只使用唯一 builder：前三者 v6、Finalizer v2、Final Auditor v4。步骤未完成与参数失败留在当前步骤；计划调整必须有阶段或目标缺口依据。任务、阶段和步骤数量不设固定上限，资源耗尽只能中断或阻塞。详见 [链路契约](CONTROLLER_ROLE_LINK_CONTRACT.zh-CN.md) 和 [唯一规范](G1J_UNIFIED_PROTOCOL_ITERATION_PLAN.zh-CN.md)。

- Planner / Stage Checker：独立强模型 `deepseek-v4-pro`，唯一配置 `.env.local`，stream=true、thinking=enabled、reasoning_effort=low；本次切换预注册输出上限分别 32768 / 16384，读取预算 600 秒（本次已完成探针为 240 秒）。owner 已切换官方 `https://api.deepseek.com`，模型列表鉴权 HTTP 200，实际完整计划请求已通过，一次 HTTP 尝试、自然 stop、4 阶段 6 步，200.37 秒；此前第三方网关 `https://next-token.cc/v1` 多次返回 `new_api_error/do_request_failed`。不能据此推断模型生成了错误计划；UltraData R4 另有一次 HTTP 200 后流协议拒绝，旧轮未保留原始 SSE，具体事件原因仍未知。
- Selector：已部署 2.9B，GPU 2，`rwkv-lh-selector-current.service`，本地端口 29621。32 层、40×64 State 已通过既有至 16384 tokens 的 Native 前向与反向机制验证；优化器未运行。
- Executor / 两个 Auditor / Finalizer：13.3B，`rwkv-lh-native-current.service`，GPU 0，本地 29613 → 服务器 18234。独立角色 zero，不复用未验证的旧 State。
- 当前部署根 `/home/chase/GitHub/RWKV-LH-official-planner-repair-r1-final-20260910`；项目 131 文件 manifest SHA `0953f64292f0a0411ca42f9b8b5f7452af5cec11b8b3f12c90c5976a927434e0`，engine 6393 文件 manifest SHA `07bb8f39eba57b513e862bf23dd439e11cd264a03ce1c942678d140466c2b352`。服务器没有使用 Git；当前服务仅导入上传的唯一项目实现。Native build 身份为 `4970b89a548fc5b1dffbbdff91c3be2021f3cd953c934d343458b576e48b5c35`。

## StateTune 的真实进度与下一步

Owner 已授权逐角色推进并取消固定三轮上限，按预注册指标、预算和实际 optimizer steps 管理；授权持续有效，不重复询问。Agent 低分和后序角色未到达不构成首轮训练禁令。

当前角色是 Selector。**当前有效候选状态以本文最上方最新段落为准**：已双签生效的是范围化 waiver `SCOPED_EQUIVALENCE_WAIVER_ACCEPTED.json`（新 14 来源、仅 Selector，排除 RP-WEB-02），提取恢复 60 条自动候选（train 55 / dev 3 / confirmation 2）、126 条待独立复核，原 9 边界/27 行完整保留；候选仍 INVALID——**execute=0**（原 15 条 execute 覆盖全部来自被排除的 RP-WEB-02）且 281 对跨切分比较有 101 对超过 0.95。历史全量数字（81 条、386/113 对）属旧 15 来源版本，仅作背景。execute 覆盖的正确补法是用修复后代码重跑含命令路径的采集，不是扩大 waiver。独立复核不能冒充双人人工签名。

补充当前来源准入状态：命令入口修复改变 harness.py 后，当前抽取器要求几乎全部生产源码 SHA 相等，15/15 原来源均被拒绝；不能声称只完成复核即可按当前代码冻结。执行证据与传输修复 R1 落地了兼容准入通道并已实际使用一次（上述范围化 waiver）；原 `EQUIVALENCE_WAIVER_DRAFT.json` 因 reviewer one 不予 accept 保持 draft，未再使用。**注意 waiver 绑定精确 SHA 对：审计接线修复 f34e4964 及其后补丁改动了 model_session.py / runtime/openai_compat.py 等文件，已生效 waiver 对新源码失效，下一次等价复核必须覆盖全部新改动文件**（完整性保护未撤销：字节重建、协议 SHA、token 回放仍无条件生效）。详见剩余问题审计与修复轮的 `PROBES.json`。

R2 实际数值边界验收已封存；正式数据/训练/Selector 回归入口已接通。通用命令执行缺陷已修复且完整回归通过，原采集结果保持封存；下一次 Agent/训练须绑定实际客户端源码与服务身份。当前角色数据合格后执行已授权 StateTune，合格前序 State 固定后采集下一角色。不得为凑样本修改家族身份、降低门槛或合成角色场景。训练须记录模型/数据/训练器身份、初始化及输出 State、预算、实际 steps 和验收结果；历史次数未知保持 unknown。

已封存结果不续跑或重评分。Real Agent Holdout V2 保持隔离，未读取，仅最终验收一次使用。Owner 负责 push；本地已提交 R4 `70f5ae0a`、REALPROJECT R1 `f9a37498`，各轮完整 SHA 清单位于实验目录的 `EVIDENCE_SHA256.json`。

历史回查：UltraData R2/R3 可核对的 22 次已提交生成全部已存在 +2 token 偏移，另 9 次未证明；见 [历史审计](../data/experiments/NATIVE_BOUNDARY_HISTORY_AUDIT_R1_20260910/REPORT.zh-CN.md)。官方切换的请求、预算和脚本局限见 [DeepSeek 验证](../data/experiments/DEEPSEEK_OFFICIAL_PLANNER_R1_20260910/REPORT.zh-CN.md)。
