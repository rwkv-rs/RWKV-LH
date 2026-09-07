# RWKV-LH 项目工作规范

本文件对所有在本仓库工作的人和自动代理生效。执行细节（唯一协议、数据生成、验收门槛、分析方法）见
`docs/G1J_UNIFIED_PROTOCOL_ITERATION_PLAN.zh-CN.md`；当前状态见 `docs/HANDOFF.zh-CN.md`。

## 1. 执行环境

- 项目命令、测试、分析与验证只在 WSL `UbuntuRecovered` 中执行，不在 Windows 端执行项目逻辑。
- **服务器禁止使用 Git，只能从本地上传。** 所有 Git 版本管理与查询（包括 clone/fetch/pull、commit、rev-parse/status 和历史查询）仅在本地执行；通过 SSH 配合 rsync/SCP 上传已冻结的源码和清单。服务器启动、部署、健康检查及身份核验不得调用 Git。
- engine 身份使用本地生成并上传的完整源码文件清单：登记相对路径、逐文件 SHA-256 和 manifest 自身 SHA-256，服务核对实际文件与冻结清单一致。不得以远端 `git rev-parse` / `git status` 代替文件身份，也不得在清单缺失或不一致时退回 Git；部署与运行证据在本地记录关联的提交和清单 SHA。
- 用 `uv sync --frozen --extra selector-runtime --extra benchmark-web --group dev` 准备完整环境，再运行 `.venv/bin/python -m playwright install chromium` 安装浏览器；测试用 `.venv/bin/python -m pytest -q tests/`，提交前必须全绿且不得跳过 Torch / State 注入或必需的浏览器验证。默认测试工件写入 `data/test_runs/pytest/`。
- 临时分析、调试和验证脚本统一放在项目根目录 `temp/`，用绝对路径执行，文件名清晰、唯一并说明用途。`temp/` 不是生产代码，`rwkv_lh/`、`scripts/`、`tests/` 不得依赖它。

## 2. 协议唯一性

- 每个模型角色只有**一个**协议模块和**一个**输入构造函数（规范 §1 表）。生产链路、StateTune 数据生成、验收评测必须调用同一函数构造输入。
- `scripts/`、`temp/`、`tests/` 中不得手写协议字典字面量（`current_progress`、`execution_state`、`gap_catalog` 等）。
- 新增协议版本时必须删除旧协议模块、渲染器、兼容入口与旧字节码，不留 identity stub 或本地归档；入口只接受当前模块常量指定的版本，所有旧版和未知版本一律拒绝。
- 运行时 attestation 标签（`goal_state_protocol`、`input_protocol`、decoder manifest）必须引用协议模块常量，不得硬编码字符串。

## 3. 数据与实验

- 实验、测试与验证数据统一放在 `data/`，按来源、版本、用途分层；每个数据集的 manifest 必须记录来源 run、生成脚本 SHA、协议模块 SHA、切分算法、相似度参数、覆盖度审计结果。
- 角色数据只能从生产 trace 抽取（规范 §2.1）；禁止合成生成器自行发明场景；禁止重放已退役 schema 的数据集；禁止为通过某道题写路径/后缀特判。
- 每角色一份不变的回归集；每一轮候选都在同一回归集上与 zero 比较，不得每轮重新生成 dev/confirmation。
- 未经 owner 书面确认，不得启动训练、不得新建 `data/datasets/` 版本目录。
- owner 已于 2026-09-07 授权 `data/datasets/rwkv_lh_real_project_dev_v1/` 的 12 题开发评测：CLI、数据、HTTP API、维护、Web、全栈各 2 题，运行器标识 `realprojectdevv1`。来源是按需求编写的开发基准，不是采集的真实用户 trace；此授权不新增角色训练额度，也不允许把参考实现直接当作 StateTune 角色数据。私有黑盒验收和作者 reference/mutant 不进入 Agent workspace；Web/全栈须实际运行 Playwright，验证器在隔离环境中读取只读 workspace snapshot。
- 角色轮次按实际训练累计；换数据版本、回退初始化或 replacement 命名不重置计数，任何角色禁止第 4 轮。Selector 已满 3 轮；Executor / Step Auditor 的“剩 1 轮”与已有 Round3 登记冲突，在 owner 对账确认前没有可自动使用的训练额度；Final Auditor 最多 3 轮。
- 旧角色数据、生成/评测链与旧实验从工作树直接删除，不保留 retired/archive 副本；历史只从 Git / GitHub 记录查询。未跟踪文件不会自动进入远端历史。本轮清理仅保留路径、SHA 和验证记录。

## 4. 对比实验纪律

- 对比两臂之间禁止修改 `rwkv_lh/` 下任何文件；改了必须两臂重跑，旧结果标 INVALID。
- 架构消融使用固定题集、固定参数、固定阈值、统一相似度算法；运行后不得为改善结果修改评价口径。
- 读取 confirmation 之后禁止修改评分、parser、stop boundary 再 rescore；发现的缺陷记录后进入下一轮，本轮按原始口径报告。
- 单次运行 Strict 波动约 ±3；改善量小于两遍 all-zero 的噪声带不算改善。
- 不得读取 Real Agent Holdout V2；它只在最终验收运行一次，结果不用于返工。`acceptance_tests/` 会读取保留题集，不在默认 tests/ 回归范围；冻结登记与来源位于 `data/acceptance/`，不得因清理旧实验而读取、修改或删除。

## 5. 整改原则

- 所有分析与优化以 RWKV 模型、State 传递机制和整体目标为核心；不得用外置 Head、额外模型调用、用例特判或冲突状态机掩盖模型能力。
- 每个模块只承担自己的职责；Controller 不读隐藏 acceptance、不重写 Final。
- Planner 的步骤和阶段数量由任务需要决定，不设固定数量上限；提示词、schema、计划补丁、累计未完成计划和阶段检查输入不得保留数量拦截或静默截断。任务结束由 RWKV 结合目标覆盖与执行证据判断，并通过既有完成校验；资源预算耗尽只能按中断/阻塞处理，不能伪装成完成。
- 根因位于全局数据结构、架构或通用逻辑时必须修根因；局部用例只作为问题入口，结论必须包含全局影响、上下游关系和回归风险。
- 每个修复配一个先失败再通过的回归测试。

## 6. 提交与汇报

- 每完成一轮立即本地 `git commit`，一轮一提交，提交信息含轮次 id；owner 负责 push。
- 汇报固定顺序：先 Agent 级（Strict / completed / mutation 数 / 终止原因），后角色级数字。角色级 100% 不得单独作为进展汇报。
- 分析、整改和验证过程在 `data/experiments/` 中有完整记录，结论附文件路径与 SHA-256。

## 7. 完成条件

问题只有在以下条件全部满足后才可标记为解决：

1. 根本原因明确且有可复核证据。
2. 完整数据集、全部同类场景和相关代码路径已排查。
3. 整改围绕 RWKV 核心能力，没有辅助模块取代或掩盖模型能力。
4. 系统性缺陷已修复，没有保留用例特判。
5. 预注册的指标与阈值达到，且未在运行后修改。
6. 全数据集、全流程、边界、异常和历史问题回归全部通过。
7. 没有引入新的同类问题或回归。
8. 过程在 `data/experiments/` 中有完整记录。
