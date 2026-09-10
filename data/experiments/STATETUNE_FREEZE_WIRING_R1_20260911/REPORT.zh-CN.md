# StateTune 冻结接口接通轮（2026-09-11）

单主题：`freeze_dataset`（rwkv_lh/statetune_data.py）接通 waiver 准入与筛选再现——训练预检 R2 确认的两个接口缺口（reviewer two 登记：`freeze_reproduction_passes_waiver: false`、`extract_registration_supports_row_filter_argument: false`）。不改任何数据门语义：`status=="valid"` 硬门、minimum_counts、regression 三重 pin、"首次 freeze 不虚构 prior" 全部保持。

## 改动

1. **waiver 透传**：freeze registration 可选 `equivalence_waiver: {path, sha256}`。约束是**双向绑定**：候选 provenance 记录了 admission waiver SHA 时，freeze 必须注册同一 SHA 的 waiver（否则拒绝"admitted under a waiver the freeze does not register"）；freeze 注册的 waiver SHA 必须等于候选的 admission SHA（否则拒绝"differs from the candidate's admission waiver"）。重提取以 `read_equivalence_waiver` 加载的同一文档、同一 pin 执行——freeze 精确重放候选当时的准入，不多不少。manifest 记录 `equivalence_waiver_sha256`。
2. **筛选再现**：可选 `row_selection: {path, sha256}` 指向密封的 `rwkv-lh.statetune-row-selection.v1` 文档：`kept_sample_ids`（唯一、非空）、按 split 的 `counts`（总和必须等于 kept 数）、`policy_evidence_refs`（逐个 pin 校验，指向复核处置与去重政策结果工件）。freeze 时先完成全量重提取与 `reproduced == candidate` 逐字节比对（提取审计的可再现性不变），然后按清单过滤：清单中的每个 sample_id 必须存在于重提取行（缺失即拒）、实际 split 分布必须与登记 counts 一致。train.jsonl 只含选中的 train 行，行字节仍来自重提取——筛选只决定成员，从不构造或修改行。minimum_counts 检查对生效（筛选后）counts。manifest 记录 `row_selection` 引用与生效 counts，候选审计原样保留。
3. 无 waiver、无 selection 时行为逐字节不变（既有测试回归通过）。

## 测试（tests/test_statetune_data.py，+9）

waiver 正向透传（观测重提取实参与 manifest 记录）；双向失配两负例；selection 正向重放（只冻结选中 train 行、counts 反映筛选）；六个负例（清单外 id、counts 与 kept 总和不符、counts 与实际 split 不符、重复 id、空 policy evidence、role 失配）。全套回归 **1464 passed、0 failed**。

## 训练启动判定（本轮结论）

**仍不应启动首轮 StateTune**，且这不是本接口能解决的：
- 候选 `status=="invalid"`（execute 覆盖=0）是预注册 coverage 要求，freeze 硬门不放松。新四题采集已证实 Selector 菜单完整含 check/run（43 行菜单全部解码验证），模型 13 动作零命令——是模型行为缺口，不是工程缺口。
- 即使绕过：当前 15 条 train 只有 2 种目标（list_directory×9、write_file×6）、4 个边界事件——用它训练会把 Selector State 进一步推向"永不选命令"，强化正是要修的缺陷。
- 本轮之后，**训练启动只剩一个真实前置**：取得含 execute 覆盖的干净采集（模型真的选择并成功执行 check/run 的边界）。届时：waiver（若代码再变则重签）→ 重提取 → 复核/去重 → 密封 selection 文档 → freeze（本接口）→ smoke → 首训，全链已通。

## 附注

本轮再次修改 `rwkv_lh/statetune_data.py`（在 SOURCE_CODE_PATHS 内）——下一次等价复核需覆盖本文件的新 SHA。执行 execute 覆盖采集属于模型行为问题，候选方向（各自单变量预注册，不在本轮）：任务指令显式要求运行测试/构建；Planner 计划模板在 execute 阶段步骤上声明 command 类 read/write root；Step Auditor 对 execute 阶段步骤要求命令证据（与"证据合同收紧"方向合并考虑）。
