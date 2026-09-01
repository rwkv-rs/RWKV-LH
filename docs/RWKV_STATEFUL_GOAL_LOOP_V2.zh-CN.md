# RWKV Stateful Goal Loop v2

更新时间：2026-09-01（Asia/Shanghai）

目标不是一次做成成熟 Agent Harness，而是先形成一条真实可运行、能推进中等难度任务、失败时保留可审核事实的最小链路。

## 当前唯一产品链路

```text
Immutable Goal + Causal Ledger
              │
              ▼
Strong Planner ── 嵌套 GoalPlanPatch：stage -> peer steps
              │
              ▼
2.9B RWKV Selector ── 只识别当前步骤意图并唯一选择一个工具
              │
              ▼
13.3B RWKV Executor ── 只填写已选工具参数、执行和汇报
              │
              ▼
Harness ── Action、结果、文件和 Artifact 的唯一事实权威
              │
              ▼
独立 RWKV Auditor State ── 只审核一个步骤边界
              │
              ▼
Evidence Kernel ── 校验证据、作用域、步骤 revision 和完成条件
              │
              ▼
Strong Stage Checker ── 只检查已完成阶段的一致性，advance / repair
```

Strong Planner 与 Strong Stage Checker 默认复用同一个强模型部署，但它们是两个独立、单职责调用。Stage Checker 不执行、不规划、不修改证据；`repair` 只能触发 Planner 生成新的 `GoalPlanPatch`。

## Planner JSON

Planner 输出按阶段嵌套。阶段内步骤同级，步骤不重复填写阶段号：

```json
{
  "add_stages": [
    {
      "stage": 1,
      "steps": [
        {
          "step_id": "S1",
          "objective": "读取并确认后端入口",
          "depends_on": [],
          "success_evidence": ["入口文件内容已被 Harness 观察"],
          "read_roots": ["backend"],
          "write_roots": [],
          "constraints": []
        },
        {
          "step_id": "S2",
          "objective": "读取并确认前端入口",
          "depends_on": [],
          "success_evidence": ["入口文件内容已被 Harness 观察"],
          "read_roots": ["frontend"],
          "write_roots": [],
          "constraints": []
        }
      ]
    },
    {
      "stage": 2,
      "steps": [
        {
          "step_id": "S3",
          "objective": "根据已确认接口完成联调修改",
          "depends_on": ["S1", "S2"],
          "success_evidence": ["修改已提交且验证命令成功"],
          "read_roots": ["backend", "frontend"],
          "write_roots": ["frontend/src/api"],
          "constraints": []
        }
      ]
    }
  ],
  "replace_stages": [],
  "discard_step_ids": [],
  "reason": "先并行确认两个入口，再进行依赖它们的修改。"
}
```

规则只有这些：

- `add_stages` 增加新步骤；`replace_stages` 真正替换未完成步骤；`discard_step_ids` 废弃过时的未完成步骤。
- 已有完成证据的步骤不可改写。
- 同阶段步骤不能互相依赖；依赖只能指向更早阶段。
- 同阶段的写/写和读/写根不能重叠；冲突计划在提交前拒绝。
- 阶段是屏障：本阶段全部步骤经过 RWKV Audit 和 Evidence Kernel 后，才能进入 Strong Stage Checker；Checker `advance` 后才进入下一阶段。
- Planner 不选择工具、不填写参数、不执行、不审核证据、不写最终答案。

## 每个角色只做一件事

- 2.9B Selector：输入只有当前步骤和候选工具短描述；提交唯一 eligible raw-logit argmax。
- 13.3B Executor：输入只有当前步骤和一个已选工具 schema；输出该工具参数或最终汇报。
- RWKV Auditor：每次从干净 State 启动，只检查一个已提交 Action 边界；不继承或合并 Executor WKV。
- Evidence Kernel：机械验证 Action 状态、证据来源、步骤 revision、读写根和最终完成条件。
- Strong Stage Checker：只返回 `verdict`、`gaps`、`reason`；review ID、stage、step IDs 和 evidence refs 全由 Controller 绑定。
- Harness：唯一允许产生外部事实和副作用的组件。

这能避免 RWKV 在同一调用中同时收到“执行、规划、否定执行、审核”之类互相攻击的要求。

## 阶段并发边界

当前代码已经实现嵌套阶段协议、阶段屏障、读写冲突拒绝和 Strong Stage Checker；当前执行器仍使用一条持久 13.3B Executor State，因此阶段内步骤暂时按顺序执行。

真正并发不得共享或合并一条正在生成的 RWKV State。下一实现边界固定为：

1. 同阶段每个步骤获得独立 Executor session/State；
2. 只有通过读写冲突检查的步骤才并发；工作区全局写和外部副作用串行；
3. 每个步骤独立执行、独立 RWKV Audit；
4. WKV 不合并，只把 Harness Action、Artifact 和 Evidence 事实提交到主 ledger；
5. 全部同阶段步骤收敛后调用一次 Strong Stage Checker；
6. 任一步失败保留已完成事实，并由 Planner 添加最小 repair stage，不重跑无关成功步骤。

在隔离 State 与事实合并协议完成前，不把线程并发或旧 Atom Pool 接回产品，也不宣称阶段并发已完成。

## Prompt 布局

所有当前产品输入统一采用：材料在前、唯一当前问题在最后、随后立即续写。Selector 末尾字段是 `current_question`；Executor 是 `current_requirement`；Auditor 是单一 `current_question`。每次调用只有一个角色和一个当前要求。

## 模型替换

- `RWKV_LH_SELECTOR_*`：2.9B Selector 与匹配权重、输入协议的 Head；
- `RWKV_LH_EXECUTOR_*`：13.3B Executor；
- `RWKV_LH_AUDITOR_*`：可选 Auditor；默认复用 Executor 的 13.3B 服务，但保持独立 session/clean State；
- `RWKV_LH_PLANNER_*`：Strong Planner 与 Stage Checker。

模型代际不写死在代码中。G1I、G1J 或后续权重都通过 `.env.local` 替换；Selector Head identity 必须匹配模型 SHA、协议和 Head SHA。

## 当前 G1J 结论

- 旧 G1J 2.9B + v7/S60 Head 固定开发集 accuracy `0.9509918`、macro-F1 `0.9492751`；最早失败是 raw argmax 工具分类错误，不是 `PlanPatch` 或 JSON 解析错误。
- 同一 S60/V7 dev 逐样本对比中，G1J 相对 G1I 修复 10 条但新增回归 29 条；净退化 19 条集中于多步骤 S39。该比较包含各自匹配 Head，不能外推裸模型能力。
- v7 把完整多步 Goal 放在语义尾，导致 Selector 越过当前 frontier。v8 已改为 frontier-only，但需要按 v8 重新抽取 G1J 特征并训练匹配 Head；这是 Selector Head 训练，不是 State Tuning。
- 当前 zero-State 对照中，G1J 13.3B Auditor 为 2/2，7.2B 为 0/2，因此默认复用 13.3B 权重，不额外常驻 7.2B。
- 现在不做 State Tuning。只有修正角色、输入、证据投影和 Head 后，固定数据仍稳定暴露同一模型能力缺口，才把“错误输出 -> 人工审核正确输出”登记为 State Tuning 数据。

证据见 [G1J Selector 审计](../data/experiments/G1J_STATEFUL_GOAL_LOOP_V2_WEIGHT_SWAP_20260901/G1J_SELECTOR_ZERO_STATE_DEV_AUDIT.md)、[G1I/G1J 配对审计](../data/experiments/G1J_VS_G1I_ROLE_COMPARISON_20260901/RESULT.md)、[13.3B/7.2B Auditor 对照](../data/experiments/G1J_ZERO_STATE_ROLE_CANARY_20260901/AUDITOR_MODEL_COMPARISON_RESULT.md) 和 [本轮整改记录](../data/experiments/RWKV_GOAL_LOOP_V2_CLEANUP_20260901/PREREGISTRATION.md)。
