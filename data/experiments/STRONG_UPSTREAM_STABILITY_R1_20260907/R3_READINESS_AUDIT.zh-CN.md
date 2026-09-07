# 双零 R3 准备审计：尚未冻结或运行

日期：2026-09-07。Agent 级：本子任务没有新增 Strict / completed / mutation / 终止原因指标，没有模型或网络调用。仅审查当前本地代码、旧登记和已授权 12 题开发集的文件身份；未读取 `.env` 凭据、Holdout、封存验收或 SQLite。没有创建 R3 执行目录，没有修改 R1/R2 冻结记录、评分或角色数据集。

当前阻塞项由 root 确认：项目配置与继承环境没有可用的旧强模型凭据，正等待 owner 提供授权配置位置或配置 `.env`。本审计不搜索其他应用凭据。上游稳定性、最终模型和配置仍为 **PENDING**，此文不能作为启动授权或已冻结证据。

## 1. 已核实的固定基础

本地观察到的 HEAD 为 `2d9b927321af8d018dbe0e11801b07f722d670f9`；这是准备时源码，不提前冒称最终 R3 冻结提交。R2 原冻结提交为 `eab0a6997ff8048f585a1a61ee5d10f361af9ffb`。当前 runner、`benchmark_verifier.py`、开发套件入口/编译 tasks/编译 acceptance、作者数据集 MANIFEST、指标 collector 共七项 SHA 与 R2 清单逐一相同。**新 R3 无需改题或评分；已有生产变化位于计划规模与 Supervisor 适配等代码，必须重新冻结两臂。**

机器证据见 [R3_READINESS_AUDIT.json](R3_READINESS_AUDIT.json)，SHA-256：`cf94690c9c0e10928997088bebf43a948cb09e0affe5ae8eae09148291771cd6`。其中记录七项完整新旧 SHA、当前源码 SHA、协议常量和来源清单。

固定 suite 为 `realprojectdevv1`，完整顺序与 R2 相同，每遍 12 题：

```text
RP-API-01, RP-API-02, RP-MAINT-01, RP-MAINT-02,
RP-CLI-01, RP-CLI-02, RP-DATA-01, RP-DATA-02,
RP-FULL-01, RP-FULL-02, RP-WEB-01, RP-WEB-02
```

它是 owner 授权编写的开发项目基准，不是采集的真实用户 trace。保持原私有黑盒和 Playwright 验收、隔离只读 workspace snapshot；不运行其他套件，不使用 `--case`、`--max-cases`、`--retry-failures-from` 或选择性补跑。

## 2. 旧驱动不能直接用于 R3 的原因

| 现有组件 | 核实结果 | R3 所需处理 |
|---|---|---|
| `temp/run_frozen_zero_baseline_r1_20260907.py` | `ROUND` 固定 R1 实验目录，`future_argv()` 固定 `_r2` 输出，输出 guard 也只接受旧目录。Strong 模型从生产 loader 读取，没有强制旧 provider；但采样说明无条件写 provider default，对 native 后端不准确 | 新建独立 R3 配置驱动；保留共享协议模块常量、五角色 zero 覆写和别名同步，显式登记最终 Strong backend/model/实际 wire。不可改旧驱动来回填历史 |
| `temp/execute_frozen_real_project_baseline_r1_20260907.py` | 固定 `REVISION='R2'` 和已有 `FROZEN_EXECUTION_MANIFEST_R2.json`。没有硬编码旧 commit；冻结时记录本地 HEAD，执行时比较旧清单内全部 SHA/依赖。当前源码变化会正确拒绝旧清单 | 新建 R3 wrapper 和新清单；绑定当前全部源码、题集、评分、lock、依赖、配置、脚本、指标与远端清单。只在 root 确认稳定/配置后创建一次 |
| 原冻结核验 | `verify_frozen` 校验源文件和依赖，但不独立比较 HEAD；公开配置只在每臂前检查，臂后只有源码与远端检查 | 新 wrapper 应明确核对本地冻结提交，并在每臂前后均核对脱敏配置/源码/依赖/服务身份。不要把变动的采集时间戳纳入稳定身份摘要 |
| `temp/collect_zero_project_metrics_r1_20260907.py` | 支持显式 `--definitions`，输入输出允许新的 experiments 子目录；当前 SHA 与 R2 一致 | 原文件逐字复用，只将命令参数绑定新 R3 指标文档与两臂路径，不改计算算法 |
| `METRIC_DEFINITIONS_R2.json` | 身份、轮次、collector 参数与最终清单名称仍指向 R2；实际 metrics/aggregation 固定 | 日后新建 R3 文档，仅更新登记元数据、源 SHA、最终 Strong 配置与路径；保持全部指标定义、缺失处理和门槛不变，并比对相应 JSON 子树 |
| `temp/compare_zero_project_arms_r2_20260907.py` | 明确要求 `registration_revision == 'R2'`，输出 schema 也为 R2 | 新建 R3 比较脚本，只调整本轮登记绑定；保留逐题完整性、source/collector/definitions/freeze 绑定、unknown 与原 N 公式 |
| `temp/attest_current_zero_remote_r1_20260907.py` | 使用 systemctl、已上传完整 engine manifest、逐文件 SHA、权重 metadata；未调用服务器 Git。脚本 SHA、PID/服务状态和全部生产 Python 源码均纳入快照 | 核验脚本和完整清单与当前服务匹配后重新采集本轮身份；不能用 R2 旧 PID/源码快照冒充当前身份。所有 Git 只在本地，远端只接收本地上传 |

冻结 wrapper 的 `source_paths()` 会覆盖 `rwkv_lh/`、`scripts/`、`tests/`、`pyproject.toml`、`uv.lock`，因此新的原生传输模块也应被纳入；不要只手工选择改动文件。数据集绑定仍使用明确的开发目录，不扩展到 Holdout 或 `data/acceptance/`。

## 3. Strong 上游配置与稳定性待确认

当前生产 `_RESPONSES_API_PHASES` 为空。选择 `backend_profile='openai-compatible'` 时，**Planner 和 Stage Checker 都是 `/chat/completions` + 当前 JSON mode**；不能把旧文档中的 Planner Responses 路径当成已启用事实。只有 root 以实际证据确认存在新格式缺陷并完成根因修复及红绿回归后，才可更改生产传输并重新登记。

最终 Planner 模型、Stage Checker 模型、base URL、授权凭据配置、重试/backoff、缓存与 fallback 均待 root 确认。可能的模型名字不是冻结值，不能现在写成已选择。Planner 默认输出预算 8,192、读取超时 240 秒；Stage Checker 输出预算仍为 2,400，其余四个 RWKV 生成角色的预算和采样不变。openai-compatible 目前没有显式发送 temperature，必须登记 provider default 的实际限制，不注入接口未支持的参数。缓存应关闭、fallback 应为空，以免跨臂复用旧计划或静默切换 Strong 模型。

`GET /models` 或健康成功只证明目录可访问。root 的稳定性检查应使用当前生产构造的完整 Planner 请求和有明确来源的合法 Stage Checker 请求，分别记录 HTTP 状态、耗时、结束原因、JSON 与角色合同结果；连接 fixture 要标注真实 Harness / mock 审计来源，不能进入基线或训练。凭据及当前稳定性未确认前，本地预检不得替代真实接口证据。

计划步骤、阶段及依赖数量不设固定上限，字段/依赖/phase/根路径与 RWKV 完成证据规则仍生效。上下文仍是物理限制，不能静默裁剪计划、删事实或改预算来放行；结束不能由步数或资源预算自动宣告。

## 4. root 确认后的具体操作顺序

1. 等待 owner 的授权凭据配置与 root 对两个 Strong 角色的稳定性结论。当前停止在此处，不冻结，不创建 R3 执行目录，不发生成。
2. 若稳定，确认最终模型/base URL/`openai-compatible` Chat 路径以及所有公开参数。使用生产 loader 构造脱敏配置；处理 canonical 与 legacy 同名参数冲突，绝不打印或写入密钥。五个 RWKV 角色显式 zero，保留当前架构、协议常量、Selector decoder、模型 SHA、`native_required`、request State delivery 与关闭 profile routing。
3. 在独立 `data/experiments/ZERO_STATE_AGENT_BASELINE_R3_20260907/` 创建新预注册和指标绑定；此目录现在尚未创建。固定新 A/B 独立 workspace、State 与输出目录，保留完整 12 题顺序。准备新配置、执行和比较脚本，仅复用旧 collector 算法。脚本位于 `temp/`，使用绝对路径，不被生产代码依赖。
4. 用新 wrapper 的配置/预检模式重新核对服务、原生 State、Selector、Strong 模型目录，以及本地上传源码和完整 engine 文件清单。绑定当前最终 HEAD、相关文件 SHA、完整依赖和已通过的完整 tests 证据；若生产再变化则完成相应回归后重新选定最终源码。服务器不运行 Git。
5. root 审核完整待冻结材料后只创建一次 `FROZEN_EXECUTION_MANIFEST_R3.json`；绑定预注册、指标文档、collector、比较脚本、argv、公开配置与远端身份。不存在的文件、PENDING 字段或未确认配置必须阻止冻结/启动。
6. 依次运行完整 A、B；每臂前后检查同一冻结身份。runner 参数保持 `--suite realprojectdevv1 --supervisor openai --supervisor-strategy goal_stages --stateful-goal --independent-selector --max-transitions 200 --tool-disclosure-mode progressive --concurrency 1 --supervisor-pending-resume-attempts 0`，仅输出目录不同。不得直接在普通 shell 跑裸 argv 而绕过进程内 zero 覆写和冻结校验。
7. 每臂收尾关闭 Controller/客户端后，按冻结 `metric_argv` 运行原 collector，必须显式 `--definitions` 指向新 R3 文档。完成记录绑定 freeze SHA、实际 runner exit、完整题序、臂前后源码/配置/部署不变证据，再只读比较两臂派生指标。

## 5. 不改变的评分与比较纪律

Strict 继续使用原 runner `passed`：Agent completed、外部验收通过、Final 非空且逐字节来自 RWKV、无验收引用泄露、bubblewrap 验收与 Agent 进程树关闭均成立。collector 继续按唯一 action / causal event 统计 mutation、目标拒绝、终止和 DB 主文件+WAL+SHM 的逻辑字节；缺失始终 unknown，不补零。

固定门槛仍为每臂 mutation > 0、operation-target invalid = 0、每题已知 DB 总大小 ≤100,000,000 bytes、没有 controller slice/总 transition 预算耗尽；完整 12 题分母不变。Strict 不新增临时最低分，双零 N 仍为 `abs(Strict_A - Strict_B)`，保留逐题翻转，N=0 不证明完全确定；没有候选时不报能力增益。

runner exit 2 可以表示完整 12 题运行结束但有 Strict 失败；不能将它与身份破坏混为一谈。exit 3 表示不可重试的上游错误触发提前停止，可能只有部分 results。后者必须保留 12 题预期分母并报告 missing/unknown，不能拿 stdout 的已执行题数当分母，不能按 runner 建议仅补 `--retry-failures-from` 后拼成双零完整臂。

两臂之间生产代码、题集、评分、parser、stop boundary、模型和参数不得改变；必要修复后保留原始证据，比较作废并重新冻结两臂。没有训练、没有新角色 datasets；角色轮次与 Holdout 限制仍按 AGENTS 和统一规范执行。
