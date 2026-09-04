# RWKV Stateful Goal Loop v3

更新时间：2026-09-04（Asia/Shanghai）

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
Controller Mechanical Evidence Gate ── 校验成功 Action 是否覆盖 read/write roots
              │
              ▼
独立 RWKV Auditor State ── 只审核一个步骤边界
              │
              ▼
Evidence Kernel ── 再校验证据引用、作用域、步骤 revision 和完成权限
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
- Planner 只声明步骤、依赖、`success_evidence` 和 read/write roots；这些声明是需求，不是完成证明。
- Planner 不选择工具、不填写参数、不执行、不审核证据、不声明步骤已经完成、不写最终答案。

## 每个角色只做一件事

- 2.9B Selector：每个 `(step_id, step_revision)` 有一条局部 WKV；同一步内更新，换步骤或进入 Final 时重置；提交唯一 eligible raw-logit argmax。
- 13.3B Executor：每个 action 从干净角色 State 启动，只输入当前步骤及其明确依赖的 Harness 事实和一个已选工具 schema，只输出该工具参数。
- Controller Mechanical Evidence Gate：依据真实成功 Action 的参数检查 read/write roots；覆盖不全时直接生成确定性 gap，不调用 Auditor，也不给完成权限。
- RWKV Auditor：每次从干净 State 启动；只在机械证据齐全后判断 Planner 的自然语言 `success_evidence`，不继承或合并 Executor WKV。
- Evidence Kernel：对 Auditor 引用的 Action 状态、证据来源、步骤 revision、读写根和最终完成条件再次 fail closed。
- Strong Stage Checker：只返回 `verdict`、`gaps`、`reason`；review ID、stage、step IDs 和 evidence refs 全由 Controller 绑定。
- Harness：唯一允许产生外部事实和副作用的组件。

这能避免 RWKV 在同一调用中同时收到“执行、规划、否定执行、审核”之类互相攻击的要求。

## 阶段并发边界

当前代码已经实现嵌套阶段协议、阶段屏障、读写冲突拒绝、Strong Stage Checker 和每 action 独立 Executor State；阶段内步骤仍暂时按顺序执行。

真正并发不得共享或合并一条正在生成的 RWKV State。下一实现边界固定为：

1. 为同阶段每个步骤分配独立事务，而不是共享一个在途 Controller boundary；
2. 只有通过读写冲突检查的步骤才并发；工作区全局写和外部副作用串行；
3. 每个步骤独立执行、独立 RWKV Audit；
4. WKV 不合并，只把 Harness Action、Artifact 和 Evidence 事实提交到主 ledger；
5. 全部同阶段步骤收敛后调用一次 Strong Stage Checker；
6. 任一步失败保留已完成事实，并由 Planner 添加最小 repair stage，不重跑无关成功步骤。

在隔离 State 与事实合并协议完成前，不把线程并发或旧 Atom Pool 接回产品，也不宣称阶段并发已完成。

## 全局状态与局部状态

- 全局权威状态是 append-only causal ledger：Goal、PlanPatch、Action、Artifact、证据、审计和 checkpoint 身份都从这里恢复。
- Planner step 的局部状态由 `(step_id, step_revision)`、该 revision 的 Action、已完成直接依赖的证据和最新 gap 投影得到；它不是第二套可冲突的状态机。
- Selector WKV 只在这个局部 step scope 内持续；Executor WKV 只活一个已选 action；一次参数修复可复用该 action handoff，选择新工具时重置。
- Step Auditor、Finalizer、Final Auditor 都是一次边界一个 clean State；它们的生成 State 不写回其他角色。
- WKV 是可丢弃加速与角色偏置，不是完成事实；完成权限只来自 causal ledger 上通过机械门和内核校验的审计记录。

## Prompt 布局

所有当前产品输入统一采用：材料在前、唯一当前问题在最后、随后立即续写。Selector 末尾字段是 `current_question`；Executor 是 `current_requirement`；Auditor 是单一 `current_question`。每次调用只有一个角色和一个当前要求。

## 模型替换

- `RWKV_LH_SELECTOR_*`：2.9B Selector 与匹配权重、输入协议的 Head；
- `RWKV_LH_EXECUTOR_*`：13.3B Executor；
- `RWKV_LH_AUDITOR_STEP_*`、`RWKV_LH_FINALIZER_*`、`RWKV_LH_AUDITOR_FINAL_*`：独立角色；默认复用 Executor 部署但保持独立 session/clean State；
- `RWKV_LH_PLANNER_*`：Strong Planner 与 Stage Checker。

模型代际不写死在代码中。G1I、G1J 或后续权重都通过 `.env.local` 替换；Selector Head identity 必须匹配模型 SHA、协议和 Head SHA。

## 当前 G1J 结论

五个角色数据集已生成，但 State 训练仍未开始。旧 Selector Head 存在独立样本冒充持久轨迹的问题，已被 runtime identity 淘汰；新 Head 必须来自同分布持久因果序列。完整合同见 [G1J 分环节 State Tuning 冻结实施协议](G1J_STATE_TUNING_AUDIT_HANDOFF_20260902.zh-CN.md)。
