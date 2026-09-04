# Round140：兼容 Stage Schema 后的并行 RWKV 原子 Canary 分析

## 结论

Round140 证明 stage schema 传输问题已解决，也证明 GPT→并行 RWKV 的主链能够完成真实任务；但 Canary 门失败，不进入 Full90。

- `E2E-B04`：external pass，完整经过 work → read-only finalizer → exact acceptance。
- `E2E-LH06`：两个首阶段 work atom 的模型执行时间真实重叠，但最终 JSON schema 错误且存在越界尝试，external fail。
- `E2E-M16`：首个过大的 work atom写出错误 schema 后中断；GPT 两次继续引用失败依赖，本地 fail-closed，external fail。
- 总计：`1/3`，不满足 `3/3`。

原始记录位于：

`data/experiments/Round140_gpt_stage_parallel_rwkv_atoms_canary_B04_M16_LH06_20260822/`

## 已验证的正向能力

1. Provider-facing stage schema 修复有效：本轮三题均成功得到 GPT stage，未复现 Round139 的 404/500 schema 错误。
2. B04 的两个请求产物正确，外部验证通过；顶层输出逐字来自 finalizer RWKV，controller 未改写。
3. LH06 的 `atom_1_resolve_requirements_json` 与 `atom_2_write_evidence` 同时于 `07:16:35` 启动，分别结束于 `07:18:48` 和 `07:17:17`，证明多个 RWKV lane 确实并行，而非仅计划层并行。
4. 写域冲突校验和失败依赖校验生效；M16 在 GPT 连续引用 interrupted atom 后 fail-closed，没有把失败依赖伪装成成功。

## 系统根因

### 1. 子 RWKV 的激活任务仍然是完整父请求

atom objective 被放在 `constraints`，但沿用 R126 的 request-last 排列后，最靠近 RWKV continuation 的仍是完整父请求。结果是“写 EVIDENCE.md”的 atom 同时尝试写 `resolved_requirements.json`，“写 resolved_requirements.json”的 atom反复尝试写 `EVIDENCE.md`。这不是单个用例提示词问题，而是 atom 身份没有进入模型主任务位。

### 2. 失败 atom 直接污染共享工作区

LH06 中两个写 `resolved_requirements.json` 的 atom 都是 interrupted，但它们的残留文件仍在共享 workspace。Planner 随后只看 manifest 便误以为物化完成，连续派发 finalizer，最终接受了建立在失败副作用上的候选。失败状态与工作区状态不是同一事务，破坏了证据权威。

### 3. Planner 没有可执行的失败恢复图约束

静态本地校验只允许 depends_on 指向 completed atom，但 provider schema 仍允许 GPT输出任意字符串。M16 两次把 finalizer 依赖指向 interrupted work atom，semantic repair 耗尽后整题中断。失败原子应当从 schema 级依赖候选中排除，并通过新 work atom重做，而不是靠自然语言提醒。

### 4. finalizer 生命周期过宽

LH06 连续产生 4 个 finalizer，只有一个 material correction stage。旧状态机没有要求 finalizer 依赖全部成功 work，也没有禁止“没有新 work 就重复 finalizer”，导致 Planner用重复复核掩盖物化失败。

### 5. 原子工具面仍是完整工具面

只读 finalizer 仍能看到写工具，普通文件 writer 仍能看到 `run_command` 等无关副作用工具。范围是在执行时拒绝，而不是在 RWKV 选择前收窄，产生了 3 个带越界尝试的原子和无效循环。

### 6. 输出合同不够明确且原子过大

M16 把 5 组 primary/fallback 读取、有效性判断、汇总、写入和验证塞进一个 atom，最终写成按 id 映射，而非请求要求的 `items` 列表与 `sources` 映射。LH06 使用 `authority_source` 而非 `source`。强 Planner没有把用户蕴含的输出键/shape 明确交给 assembler，RWKV承担了过多跨步骤结构推断。

## 架构级整改（v2）

1. 每个 atom 使用独立 workspace snapshot；只有 `completed` atom 的声明 `write_roots` 才合并到父 workspace。failed/interrupted atom 的残留永不成为 Planner 公共证据。
2. 子 RWKV 的 active immutable request 改为 atom objective；父请求保留为不可修改的引用约束，解决任务身份邻接错误。
3. dependency outcome 以公开 handoff 注入下游 RWKV；assembler 可消费已完成 scout 的结果，而不是重新做全任务。
4. provider schema 动态把 `depends_on` 限定为 completed atom id；失败 id 在生成结构层不可选。
5. finalizer 必须只读、非 exclusive、单独运行、依赖全部 completed work；未恢复的 failed work 会阻止 finalization；没有新 correction work 时禁止重复 finalizer；accept 只能选择最新且不陈旧的 finalizer。
6. RWKV 工具面按 atom 权限收窄：read-only 不展示写/副作用工具，普通 scoped writer 不展示 `run_command` 等非路径副作用工具。
7. Planner 指令要求独立输入优先拆成 2–4 个并行 scout，单 atom 通常 1–6 个直接操作；assembler 明确用户蕴含的输出键与 shape，但不得发明观测值。

这些整改作用于所有数据集、全部任务类型和恢复路径，不包含 B04/M16/LH06 特判。

