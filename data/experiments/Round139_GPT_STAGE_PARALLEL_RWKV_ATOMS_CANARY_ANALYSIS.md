# Round139：GPT 阶段规划 + 并行 RWKV 原子 Canary 分析

## 结论

Round139 是基础设施无效运行，不能用于判断新架构或模型能力。3 个预注册用例均在第一个 GPT stage 提交前 fail-closed，中途没有产生 stage、没有调度 RWKV 原子、没有修改用例工作区。

## 固定运行与结果

- 用例：`E2E-B04`、`E2E-M16`、`E2E-LH06`
- 结果：`0/3` external pass
- 三题终态：`interrupted / supervisor_stage_unavailable`
- committed stage：`0`
- atom outcome：`0`
- B04：stage 请求 HTTP 404
- M16、LH06：stage 请求重试后 HTTP 500

原始结果位于：

`data/experiments/Round139_gpt_stage_parallel_rwkv_atoms_canary_B04_M16_LH06_20260822/`

## 根因证据

同一 `.env`、同一 endpoint、同一 `gpt-5.4` 的最小严格 JSON Schema 请求返回 HTTP 200；完整 stage schema 稳定复现 HTTP 404。移除 `allOf/if/then/else` 条件 schema 后，同一 stage 请求返回 HTTP 200 和合法 JSON。

因此根因是 OpenAI-compatible 上游不支持 stage schema 中的条件 JSON Schema 关键字，而不是 Planner 不会拆解，也不是 RWKV 原子执行失败。旧 directive schema 不含这些条件关键字，Round138 已有大量成功返回记录，与该结论一致。

## 系统整改

从 provider-facing `STAGE_RESPONSE_SCHEMA` 删除条件关键字，仅保留兼容的严格对象、必填字段、枚举和数组约束。dispatch/accept_final 的互斥约束、finalizer 权限、依赖、唯一 id、并行写作用域冲突和候选来源仍由 `SupervisorStage.create()` 本地不可绕过地校验；违反时进入已有的 bounded semantic repair，而不是放宽架构约束。

## 回归风险

- provider 现在可能返回“结构合法但 disposition 字段组合非法”的对象；本地构造器会拒绝并最多修复一次。
- 如果修复后仍非法，控制器保持 fail-closed 和 resumable，不启动未经验证的 atom。
- 本轮不改变预注册指标，也不重解释三题为能力失败。

