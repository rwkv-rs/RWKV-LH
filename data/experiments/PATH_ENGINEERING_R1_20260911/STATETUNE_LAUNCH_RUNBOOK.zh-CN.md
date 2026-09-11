# 首轮 Selector StateTune 启动运行手册（2026-09-11）

当前状态（SELECTOR_EQUIVALENCE_RENEWAL_R3 FINAL_GATE.json，逐字段核对）：**candidate_status=valid（首次）、execute_coverage=3、24 有效行/9 边界（train 19/7）**。唯一阻塞：预注册有效数据下限 **30 行/10 边界** 未达（`training_status: BLOCKED_BY_PREREGISTERED_EFFECTIVE_DATA_MINIMUMS`）。freeze/smoke/首训接口全部就绪且经真实 22 来源重放验证。

## 缺口合规补法（不降门槛、不改预注册下限）

差 ~6 行/1+ 边界。唯一合规来源是**新增真实采集**：
1. 用 diagfix2 模式再建 2 个先诊断任务（DIAG-FIX-03/04，build_suite.py 同一设计合同：预置可运行项目 + 恰一个失败测试；沿用"未修复恰一失败→验收拒绝→修复通过"的闭环验证），或复跑既有 4 题的不同 case 组合（同任务不同运行产生新边界）。
2. 采集参数照 EXECUTE_COVERAGE_COLLECTION_R2 原样（1800/并发1/200 transitions；**注意：本轮 PATH_ENGINEERING_R1 改了 harness.py/supervisor_openai.py，采集前先部署新源码并重签**——见下）。
3. 新行走既定链：双 AI 语义复核 → 相似度政策原样重跑（0.95/聚类规则不动）→ 合并后 ≥30 行/≥10 边界 → 更新 ROW_SELECTION 密封文档。

## 达标后的启动序列（接口均已存在，按序执行）

1. **等价续签**（因 R3 冻结修复 + 本路径工程轮，一次覆盖）：重建 waiver 草案 pin 最新 SHA（harness.py、supervisor_openai.py、statetune_data.py、role_trace_selection.py 及 R3 触及文件），双 AI accept；selected-source 登记按 R3 新规矩带两份范围复核文件。
2. **freeze**：`scripts/run_state_tune.py freeze --registration <freeze_registration> --registration-sha256 <pin> --output data/datasets/selector_statetune_v1`。registration 按 FREEZE_SCHEMA 填：role=selector_intent、candidate_manifest/source_registration（selected-source 文档）/row_selection/authorization/minimum_counts（预注册值）/regression_fingerprint、首次 freeze 无 prior_regression。
3. **smoke**：小步数 train 调用（同一 registration 加 smoke 预算），验收 optimizer steps > 0、zero-state attestation、tokenizer/model SHA 一致、输出 State 落盘。
4. **首训登记**：RUN_SCHEMA registration（run_id 非 zero、optimizer 参数、authorization、evaluation_registration 双 pin），`run_state_tune.py train`，产出候选 State；`evaluate` 对固定回归锚比较，KEEP 判据 = held-out 边界一致率提升且回归锚不退化。

## 明确不做

- 不为凑 6 行降低 30/10 下限、放宽 0.95、或把 dev/confirmation 行挪进 train；
- 不手工构造/复制行（seal 禁令有效）；
- 训练结果不管好坏，Agent 评分口径不变。
