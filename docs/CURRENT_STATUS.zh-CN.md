# RWKV-LH 当前状态

更新时间：2026-09-01（Asia/Shanghai）

## 结论

当前最早可证实的问题不是 `PlanPatch` 格式，而是旧链路的角色和输入错位：2.9B Selector v7 在语义尾看到完整多步骤 Goal，固定样本已经完成解析和 logits 计算，却把 `list_directory` 选成 `read_file`。13.3B Audit 的旧失败又包含两个独立工程问题：prompt 暴露禁止输出的内核字段，以及 evidence ref 没有投影对应 Harness 事实。

修正输入和证据投影后，G1J 13.3B 当前 Auditor 模板为 `2/2`，7.2B 为 `0/2`；因此默认 Auditor 复用 13.3B 服务，不启动 State Tuning。

## 当前固定架构

```text
Strong Planner
  └─ nested add_stages / replace_stages / discard_step_ids
       └─ current stage peer steps
            └─ 2.9B Selector: one tool
                 └─ 13.3B Executor: parameters/action/report
                      └─ Harness facts
                           └─ clean-State RWKV Audit
                                └─ Evidence Kernel
                                     └─ Strong Stage Checker: advance/repair
```

阶段协议和阶段检查已经实现；阶段内真实并发尚未实现。当前一条持久 Executor State 顺序推进同阶段步骤，避免共享 State 和单一 Audit boundary 产生竞争。

## 已完成整改

- 产品入口只保留 `stateful_goal`。
- Strong Planner 使用原生嵌套 `GoalPlanPatch`，未完成步骤可真正 replace/discard。
- 阶段内同级、跨阶段依赖、阶段屏障和读写冲突均由内核校验。
- Stage Checker 是同一强模型部署上的独立只读调用，模型只返回 `verdict/gaps/reason`。
- 2.9B 是工具选择唯一权威；13.3B 不再 Top-K 二次选择。
- Selector v8 只接收一个当前 frontier，并把它放在语义尾。
- Executor 一次只接收一个当前步骤和一个工具 schema。
- Auditor 使用独立 clean State；retry 不污染 Executor，WKV 不 merge。
- repair feedback 与 Planner patch 有 durable source link，恢复后不会遗漏未完成修订。
- Planner、Selector、Executor、Auditor 都可通过 `.env` 替换模型配置。

## 当前 G1J 证据

| 角色/测试 | 结果 | 归因 |
|---|---:|---|
| 2.9B v7/S60 S39 accuracy | `0.9509918`，gate `0.96` | 最早失败为工具分类；上游输入职责错位 |
| 2.9B v7/S60 S39 macro-F1 | `0.9492751`，gate `0.96` | 同上 |
| 13.3B 最新 Audit 模板 | `2/2` | 当前小样本通过 |
| 7.2B 最新 Audit 模板 | `0/2` | 格式合法，但错误忽略完整 evidence metadata |
| 13.3B selected-write 参数例 | `1/1` | 当前小样本通过 |

同一 S60/V7 dev 2571 条逐样本配对：G1J 相对 G1I 修复 10 条、新增回归 29 条、共同错误
29 条，整体 accuracy `0.984831 -> 0.977441`。净回归 19 条主要位于 S39。该结果比较的是
两代基座各自配套 Head，不代表裸模型，也不代表尚未训练匹配 Head 的 V8。

Selector v8 更改了输入 portable identity，必须按 v8 重新抽取 G1J zero-State 特征并训练匹配 Head。旧 v7 Head 不能用于声称 v8 质量通过；这属于 Selector Head 适配，不是 RWKV State Tuning。

## 当前验证

- 当前 WSL 工作区全量：`771 passed, 1 warning`；核心链定向：`240 passed`。
- 干净提交快照核心链：`240 passed`。
- 干净提交快照全量：`615 passed, 147 failed, 1 warning`；147 项均指向未纳入 Git 的
  冻结 dataset/experiment artifact，说明仓库打包尚非 clean-clone 自包含。
- warning 是 Python 3.13 多线程进程使用 `fork()` 的既有弃用提示。
- `git diff --check` 通过。

## 尚未完成

- 同阶段每步独立 Executor State 与并发事实提交协议；
- Selector v8 + G1J 匹配 Head 的固定 train/dev/locked-test gate；
- 当前最新架构上的真实 G1J 中等难度 E2E；
- 只有上述三项完成后仍可重复出现的模型能力缺口，才可转为 State Tuning 数据。

实验和 trace 定位见 [架构说明](RWKV_STATEFUL_GOAL_LOOP_V2.zh-CN.md)、[G1J Selector 审计](../data/experiments/G1J_STATEFUL_GOAL_LOOP_V2_WEIGHT_SWAP_20260901/G1J_SELECTOR_ZERO_STATE_DEV_AUDIT.md)、[G1I/G1J 配对审计](../data/experiments/G1J_VS_G1I_ROLE_COMPARISON_20260901/RESULT.md) 与 [Auditor 对照](../data/experiments/G1J_ZERO_STATE_ROLE_CANARY_20260901/AUDITOR_MODEL_COMPARISON_RESULT.md)。
