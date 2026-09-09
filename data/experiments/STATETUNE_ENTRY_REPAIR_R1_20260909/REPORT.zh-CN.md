# 工程与逐角色 StateTune 入口整改

轮次 `STATETUNE_ENTRY_REPAIR_R1_20260909`，日期 2026-09-09。结论范围：本轮定位的十类工程问题已完成代码修复与本地回归；修复后的真实 Agent 效果尚待新的冻结运行。当前文档与 owner 最新训练管理决定同步。没有开始训练、创建正式角色数据版本或部署服务。

## Agent 级证据优先

最近完整模型实测仍是历史 R7：A/B 各 Strict **0/12**、completed **0/12**、mutation **0**；各成功目录观察 12 次，原始终止 `strong_planner_unavailable` / `fixed_plan_exhausted`。本轮没有新增 Agent 指标。R7 第二个动作尚未发生，不能解释为已测到第二或第三阶段；之后的读文件、变更、执行检查、Stage 与 Final 能力未知。

角色级：每臂 Selector 12 次 handoff、36 次菜单求值；Executor 与 Step Auditor 各 12 次。固定初始计划没有 Planner 模型生成，Stage Checker、Finalizer、Final Auditor 均未调用。角色协议接受不代表审计语义正确，也不代表任务完成。

R7 原 [报告](/home/chase/GitHub/RWKV-LH-zero-baseline-r4/data/experiments/ZERO_STATE_AGENT_BASELINE_R7_20260907/REPORT.zh-CN.md) SHA `1809a26e0c53583270bb8a905b83298032da72cdde639bfca64873f055ea24ba`；原 HEAD `9d931fd18e34c18bb918b569dd1e9dec5e2d6cc6`，freeze SHA `e237c85e9705ed84d301a97132a66ddbd8668717cd9d4ec5e0c04d9c3f2a3f64`。两臂在原冻结代码内 VALID，不改写历史结果。当前源码变化后必须新冻结、两臂同代码重跑。

## 根因、全局修复与回归证据

| 编号 | 根因与上下游影响 | 通用修复 | 红测 / 绿测证据 |
|---|---|---|---|
| F01 | Controller 把所有步骤 REPAIR 视为必须改计划，首次目录观察后就耗尽固定 Planner；阻止正常第二动作 | 删除无条件规划分支，保留同一步 gap 输入、结构性重规划与相同成功动作预算；真实目录观察→读取可继续 | `controller_red.log` / `controller_green.log`，最终 Controller 全量回归 |
| F02 | kernel 接受、根推进或 completed 被误当作 Auditor/Finalizer 语义真值；有复核时还可能漏验 Executor 实际执行 | 独立双人语义复核与精确边界纠正；可见事实反证检查；待复核队列；Executor 无实际成功执行不可成为正例，所有实际动作均核对原命令 | `data_red.log`、`executor_review_red.log` / `data_green.log`、`latest_trace.log`、最终全集 |
| F03 | 请求沙箱但 bwrap 缺失时静默执行宿主命令 | 在启动任何命令前明确失败，无宿主回退 | `engineering_red.log` / `engineering_green.log`、最终全集 |
| F04 | bwrap 无条件共享宿主网络，越过既有网络策略 | 命令沙箱保持独立网络命名空间，外部网络走现有受策略约束工具 | 同上 |
| F05 | 来源判定只比整段字符串，包裹/大小写/URL 标点可洗掉私有片段身份 | 比较未由用户公开提供的词法片段与 workspace/工具来源，原出站参数不改写 | `egress_red.log` / `egress_green.log`，六类包装来源及完整 retrieval 回归 |
| F06 | prompt IDs/BOS 被会话/原生 snapshot/Selector 返回链丢弃，本地编码不能证明实际输入 | 保存实际 forward IDs 与响应元数据，按完整 scope、显式 BOS 和上下文重建严格绑定；未知保持未证明 | `input_tokens_red.log`、`selector_tokens_red.log` / `runtime_green.log`、`selector_tokens_green.log`、`latest_trace.log` |
| F07 | completion/native generate 缺失 finish_reason 被自动变为 stop | 未知保持空值，不能按自然结束通过 | `runtime_red.log` / `runtime_green.log`、最终全集 |
| F08 | 审计累计证据固定最多八条，九根及以上任务丢失后续根证明 | 每根保留最新有效证据与最新边界，取消根证据条数截断；文本预算不足继续显式阻塞 | `engineering_red.log` / `engineering_green.log`，2/9 根与额外观察回归 |
| F09 | Web 重启只知内存进程，可能重复启动同 run | 核验持久 PID，父子进程继承 OS 文件锁，覆盖 spawn 后 PID 发布失败窗口 | `engineering_red.log` / 最终真实子进程锁继承及释放回归 |
| F10 | 两个公共开发基准 JSON 未进入 package-data，安装分发可能缺资源 | 为 agent-v1 与 capability-ladder-v1 补充 tasks/acceptance 声明 | `engineering_red.log` / `engineering_green.log`，只检查这两个公共目录 |

这是本轮发现并处理的十类问题，不是“整个项目最多只有十个问题”的穷尽证明。相关生产、数据抽取、prompt replay/native、Controller 历史路径及异常边界均进入默认完整回归；没有以外置 Head、额外模型调用或题目路径特判替代 RWKV 能力。

## 逐角色数据与管理规则

当前只保留一个产品 Controller 和五个角色输入 builder。采集入口支持 `all_zero` 及运行前冻结 `role_data_collection` 的 `role_stage`：只抽取目标角色，前序合格 State 固定、目标及后序 zero，模型/State/cache/raw generation 身份逐项核验。跨上游 State 的来源不能混进同一固定角色回归。

Selector → Executor → Step Auditor → Finalizer → Final Auditor 顺序推进。每一步依据自己的预注册覆盖、样本量、标签和验证条件训练；Agent 低分、无 mutation 或后序未到达均不再是前序训练禁令。阶段验证通过的 State 可作为下一采集条件，最终组合是否保留仍依据 Agent 验收与消融。比较只换目标角色 State，其余条件冻结。

九类覆盖完整报告；可在采集前冻结当前角色的必需覆盖 scope，并由 RUN_PROTOCOL 固定 SHA。默认仍是九类全覆盖，不能看完结果后删要求。80/10/10 family 切分、byte 5-gram cosine≥0.95 拒绝、固定 dev/confirmation 不变；覆盖和采集条件也绑定回归身份。仅有一个项目家族的 fixture 不能成为合格三分数据集。

错误审计与未达后序阶段的真实输入可以进入复核队列；两人必须绑定精确输入、原始记录、可见证据、理由与相同目标。原始输出和 raw token 永远保留，纠正目标另存，并标本地 tokenizer SHA；不冒充模型原文。Executor 仍必须实际执行成功，人工复核不补造动作。当前 length/缺原始 token 的生成仍排除，不能仅靠补写目标恢复来源证据。

owner 于 2026-09-09 明确“取消固定三轮上限，改按预注册指标、预算和实际训练记录管理”。AGENTS、README、统一规范、HANDOFF、StateTune 状态和管线说明已一致更新。没有“剩余轮次”或第四轮禁令；历史未知次数保持 unknown，不伪造为零，也不作为额度门。训练开始前冻结具体 run/指标/预算，结束记录实际更新 steps、消耗、输出 State、日志与验证 SHA。详见 [TRAINING_POLICY.json](TRAINING_POLICY.json)。历史报告保留原始事实，其旧额度指令由新决策替代。

## 架构判断与仍需实测的事项

现有角色拆分有明确职责，适合先选择工具、再学习参数与执行、再训练语义判断。R7 暴露的是控制流与证据/标签链缺陷，后序角色未运行，不足以证明必须整体换角色。三菜单与每动作审计的调用成本可另做固定条件消融；本轮未改变角色划分或新增另一套状态机。

RWKV 升级复用当前输入与数据消费边界，优先改模型、词表、State 形状/精度、上下文和传输配置及必要适配。不能假定旧 State 自动兼容；没有新模型的注入、token 与真实流程验证，就不宣称跨版本已兼容。只有语义合同变化才替换协议，删除旧入口，历史留 Git/GitHub。

仍缺：修复后新生产 trace；预注册且达到样本量的当前角色数据与固定回归；匹配实际 RWKV backend 的已验证优化器训练入口；Planner 合同、Stage Checker 自然结束/上下文及后续 Agent 完成能力实测。当前 `rwkv_lh/` 和 `scripts/` 的 State 注入与抽取实现不是训练器。E2E-LH09 的 `mock_api` 生产适配冲突独立待修，不能改旧分母或恢复退役架构。未开展服务器部署或在线健康复验。

网络片段检测采用保守词法匹配，可能把常见非用户词判为敏感；它覆盖本轮复制/包装/大小写/URL 标点绕过，不证明任意编码、改写的全程污点安全。命令沙箱不再共享外网，涉及下载的流程必须使用既有网络工具。新增 trace 元数据与边界增加存储开销；完整根证据可能触发原有上下文预算，均应在新真实运行测量。Web 锁实现针对项目规定的 WSL/Linux。包数据验证检查两个公共包声明与文件，未构建会扫描受保护材料的完整 wheel。

## 验证、工作树与身份

最终完整回归：**1043 passed，0 skipped**，耗时 191.24s (0:03:11)。命令为 `.venv/bin/python -m pytest -q tests/ --basetemp=data/test_runs/pytest_statetune_entry_final_20260909 --tb=short --durations=5`。包含实际 Playwright 浏览器、本地 HTTP、Torch / State 注入及真实子进程锁测试；为允许本地 socket/网络接口查询，在 WSL 使用沙箱外测试权限。完整原始日志见 [final_full_pytest.log](final_full_pytest.log)。前一遍完整回归 1042 passed，补充 Executor 证据回归后重跑最终全集；中途失败的红测和 fixture 断言修正记录全部保留，不只保存绿测。

起始本地 HEAD 为 `d2cc5da2bb208d80aecbbc0fd39c26295a386bc7`。开始时已有未提交的 trace 管线及生产集成，本轮在其上修复并统一纳入本地提交；原状态和八个关键文件起始 SHA 见 [STARTING_STATE.json](STARTING_STATE.json)。与任务无关的未跟踪实验和受保护材料未纳入提交，不恢复旧源码/数据归档，不读取 Holdout。

本轮脚本位于 `temp/`，按绝对路径执行；生产和测试不依赖它。规范文档、源码、测试及全部本轮工件 SHA 登记于 [MANIFEST.json](MANIFEST.json)，其自身 SHA 位于 [MANIFEST.sha256](MANIFEST.sha256)。本报告 SHA 单独位于 [REPORT.sha256](REPORT.sha256)。只执行本地 Git，owner 负责 push；本次不产生远端 Git 操作。
