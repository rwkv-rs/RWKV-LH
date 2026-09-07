# 角色训练轮次：本地证据对账

日期：2026-09-07。审查基准提交：`eab0a6997ff8048f585a1a61ee5d10f361af9ffb`。双零 R2 A 已由主代理启动，本审查不读取其运行数据，也不改变生产、评分、脚本快照、题集、参数或已有登记。本次仅使用本地当前规范和本地 Git 历史；没有服务器命令、训练、数据集生成或封存资料读取。

结论：**目前不能据本地材料自动核发任何角色的训练额度。** 当前规范明确 Selector 已满三轮，Executor / Step Auditor 存在 Round3 与“剩一轮”的冲突；本次找到了更早 G1i 的 27 个真实 WKV 训练族的历史清单，但没有在本次可查材料中补齐当前 G1J 各角色逐 run 的训练完成记录。历史文档的版本内“0”不能抵消已经发生的累计训练；缺少日志也不能填作训练零次。

## 按角色的证据与限制

| 角色 | 已发生训练的历史文档证据 | 当前 G1J 计数/权限声明 | 本次能确定的对账结论 |
|---|---|---|---|
| Selector | H1 明确列出 G1i 2.9B **12 个**已执行 `peft=state` 训练族；外置 Head 训练不在其中 | C1/C3 和 H6 明确“已满 3 轮”；没有当前三轮的逐 run 完成证据可用于独立核对 | 按现行限制不得再训；不得把旧 G1J 版本状态为 0 当作重新获得三轮 |
| Executor | H1 明确列出 G1i 13.3B **15 个**已执行 WKV 训练族；G5/G6 有 checkpoint 校验记录但无逐 step loss 留档 | C1/C2/C3：旧“剩一轮”与 Round3 / final-round / replacement-Round3 登记冲突 | 当前 G1J 实际累计值及这些别名的对应关系尚未核实，不能自动使用所谓剩余额度 |
| Step Auditor | 本次所查训练清单未提供该独立角色的实际训练 run；这不是未训练证明 | C1/C2/C3 同样登记 Round3 与“剩一轮”冲突 | 不自动声明为 2 次或 3 次，须逐 run 对账；当前无可自动使用额度 |
| Final Auditor | 本次未取得独立角色实际训练完成记录；H2/H4/H7 的 0 仅描述 2026-09-02/04 当时版本 | C1/C3 规定最多三轮，没有在这些声明中给出已用次数 | 实际已用次数 unknown；“最多三轮”不是“还剩三轮”，需核实次数及 owner 授权 |
| Finalizer | 本次未取得独立角色训练完成记录 | C2 明确当前 zero、没有独立训练授权；H5 的后续计划明确不训练 Finalizer | 不能以 zero 部署推导历史训练零次；没有本轮独立训练许可 |

H1 的模型明确是 `rwkv7-g1i-13.3b-20260805-ctx16384` 与 `rwkv7-g1i-2.9b-20260805-ctx16384`，不能冒充当前 G1J 三轮的直接 run 证据，也不能静默从累计历史中删除。当前三轮限制的历史起算范围、旧 G1i 训练与新五角色的归属，必须由 owner 对账确认；本报告不擅自把 12/15 与当前声明的 3 相加，也不据换模型/版本为任何角色重置次数。

## 可查的实际训练族

来源 H1：提交 `e7df09c9c77b5fdec0b0a8a855036ab6652327a9`，历史路径 `data/experiments/STATE_TUNING_INVENTORY_V1_20260831/REPORT.md`，文档日期 2026-08-31。这里只审阅训练口径、配置和训练族清单，没有读取模型/State 二进制、训练数据、原始逐 step loss 或评测题目。

| 角色/基础模型 | 历史文档明确计入的训练族 |
|---|---|
| G1i 13.3B Executor，15 族 | Round1；Stage1、Stage2、Stage3、Stage4、Stage5、Stage6、Stage7；G3、G4、G5、G6、G7、G8、G9 |
| G1i 2.9B Selector，12 族 | S1、S2、S12、S19、S25、S27、S31、S54、S61、S67、S70、S71 |

H1 自己明确只统计真正更新初始 WKV 的 `peft=state`，区分了 Head 训练、仅预注册配置和仅数据目录。它报告 25 族有可恢复 loss，另两族 G5/G6 有 checkpoint 与校验记录但缺逐 step loss；这些是历史盘点者的已执行声明，本次没有重新验证被删除的原始训练日志，因此证据级别为**已提交历史训练盘点**，不能冒称本次逐 run 独立重验通过。

文档含 zero 初始化、continuation、从旧 checkpoint 分叉等不同来源。同一角色重新从 zero 起训、回退初始化或更换数据名称并不自动减少实际训练累计；同一训练的多个保存 checkpoint 也不能无证据地拆成多轮。角色 `Round1/Stage1/G3` 与 Agent 工程迭代 `Round119/R130` 是不同对象，后者不能按编号计作训练次数。

## 时间线与冲突的证据位置

| 证据 | 提交与历史路径 | 与本次轮次核对有关的事实 |
|---|---|---|
| H1 | `e7df09c9…`：`data/experiments/STATE_TUNING_INVENTORY_V1_20260831/REPORT.md` | 2026-08-31 G1i 已执行纯 WKV 训练共 27 族，按 15/12 分角色列出 |
| H7 | `e7df09c9…`：`data/experiments/G1J_PER_STAGE_STATE_TUNING_V1_20260902/BASELINE_READINESS_RESULT.md` | 2026-09-02 新 G1J per-stage 准备记录为 NOT_STARTED，训练/选择 State 为 0，先决门未满足 |
| H2/H3/H4 | `3f23a6a6…`：`docs/G1J_STATE_TUNING_AUDIT_HANDOFF_20260902.zh-CN.md`、`docs/CURRENT_STATUS.zh-CN.md`、`docs/CURRENT_HANDOFF.zh-CN.md` | 2026-09-04 提交的当时交接仍写五角色 `trained_stage_count=0`；描述新方案状态，不是终身累计台账 |
| H5 | `91b6cc69…`：`docs/HANDOFF.zh-CN.md` | 2026-09-04 后续交接说当前缺可用 G1J 正式数据，给出未来 Selector / Executor 训练命令，明确本轮不训练另三个角色；命令和计划本身不证明已发生训练 |
| H6 | `cf3a8337…`：`docs/G1J_UNIFIED_PROTOCOL_ITERATION_PLAN.zh-CN.md` | 2026-09-07 明确 Selector 已满 3；Executor/Step Auditor Round3 登记与“各剩 1”冲突；换版本/replacement 不重置 |
| C1/C2/C3 | 当前 `AGENTS.md`、`docs/HANDOFF.zh-CN.md`、`docs/G1J_UNIFIED_PROTOCOL_ITERATION_PLAN.zh-CN.md` | 延续上述限制；Finalizer 无独立授权，Final Auditor 最多 3 轮 |

H5 → H6 之间，本次没有取得足以映射当前 G1J 三轮的逐 run 训练完成证据。不能据此断言训练没有发生，也不能判定 Round3、final-round、replacement-Round3 必然是同一 run 或三个不同 run。当前文档的额度冲突已成立；具体累计数仍需真实执行身份来解决。

## 给 owner 的具体对账项

每个被登记为 Round1 / Round2 / Round3 / final-round / replacement-Round3 的训练需要对应：角色与基础模型 SHA、训练 run ID、开始/结束时间、训练日志路径及 SHA、是否发生 optimizer 更新及最后 step、初始化 State SHA、输出 checkpoint/State SHA、数据 manifest SHA、训练器代码 SHA，以及该 run 归属哪一次书面授权。若多个名称指向同一执行，须以实际执行记录证明；如果发生过新的梯度更新，不能只靠改名或重新初始化将其取消计数。

优先对账 Selector 当前三轮的实际身份、Executor 与 Step Auditor 的 Round3 别名、Final Auditor 已用次数和 Finalizer 是否存在历史训练。另须明确早期 G1i 15/12 族在现行累计限制中的归属，不能由审计者自行决定忽略。仅预注册、只做 Head 训练、数据生成、格式转换、checkpoint 导出、zero 推理或被中断的基线运行，不凭名称自动计作新的 WKV 训练；如果某个“失败训练”已发生参数更新，其事实需单独保留，不能按失败标签自动抹除。

本报告没有提出新的训练申请，也没有调整三轮上限。完成这张证据表之前保持现行禁止自动使用额度的状态；之后即便确认仍有合法轮次，也仍需对应 owner 书面训练许可与其他预注册门。

## 来源身份与审查范围

[TRAINING_ROUND_ACCOUNTING_SOURCES.json](TRAINING_ROUND_ACCOUNTING_SOURCES.json) 记录 10 份来源的完整提交号、历史路径、Git blob OID、内容 SHA-256、只与训练有关的指定节摘录，以及当前 57 个可达提交中发现的 60 个相关历史路径的元数据。历史路径清点不等于读取其所有正文；没有打开列出的旧评测结果、封存资料或训练数据，也没有恢复旧协议、数据链或完整历史文档副本。

来源记录 SHA-256：`b1b1b3d9550e2fe7a158119632b0c8a5cddc7f0c203a7c0d0386636d7004a907`。记录脚本为 `temp/record_training_round_accounting_sources_20260907.py`，使用绝对路径在本地 WSL 执行，脚本 SHA 保存在来源记录中；它不属于生产或冻结双零执行链。
