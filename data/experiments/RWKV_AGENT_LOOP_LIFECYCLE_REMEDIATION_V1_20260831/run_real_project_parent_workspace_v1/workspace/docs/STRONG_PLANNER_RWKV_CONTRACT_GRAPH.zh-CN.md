# Strong Planner / RWKV Contract Graph 架构

## 目标

强模型负责理解、拆解和审核；RWKV 负责所有工具参数、工具执行、失败恢复与最终回答。控制器只执行
确定性调度、权限检查、事务合并和证据记账，不推导业务内容，不替任何模型写答案。

## 为什么不是逐轮 Stage Loop

Round148 的逐轮 stage loop 已证明并行执行有效，但同一个 GPT 调用既延续自己的计划解释、又决定
是否接受，导致错误解释自我确认；固定 stage 上限又把 finalizer 的格式重试变成业务返工。每轮重建
自然语言计划还会重复上下文，并在并发 case 下放大强模型 API 压力。

Contract Graph 将“业务是否完成”从某次自然语言判断改成持久化、可引用、单调推进的义务账本。

## 四层结构

### 1. Immutable Contract / Obligation Ledger

Planner 首次读取 immutable request、公开 workspace manifest 和 operation catalog，编译出稳定义务：

- `obligation_id`：全局稳定 ID；
- `request_clause`：原请求的 verbatim 子串或稳定字符区间；
- `predicate`：对最终公开状态/因果状态的可审核条件；
- `evidence_kind`：需要的 file/json/digest/command/event/API 等证据类型；
- `status`：open / satisfied / contradicted；
- `evidence_refs`：只允许引用精确工具或父因果事件 ID。

全部 obligation 都是 mandatory；Planner 无权输出 `required=false`。完整义务集合只允许在 revision 0
生成，此后永久冻结；修正 patch 只能追加节点，不能新增、删除、改写或收紧用户契约。

### 2. Planner Graph Patch

Planner 不输出完整新计划，只对持久化 DAG 追加 node patch：

- 新增一个或多个 ready RWKV atom；
- 每个 atom 绑定一个或多个 obligation IDs；
- exactly one operation kind；RWKV 自己生成参数；
- 显式 depends_on、read_roots、write_roots、exclusive、action_budget；
- 不允许 `accept_final`，也不允许 Planner 写 artifact 内容或 Final。

Planner 只在三个边界调用：初始编译、Reviewer 报告 evidence gap、真实失败/矛盾后重规划。正常 ready
nodes 由调度器连续执行，不需要每个 batch 再问 GPT。

初始 patch 同时登记一个 frozen read-only finalizer，并令其依赖全部初始 work nodes；它在 Reviewer
关闭全部 mandatory obligations 前不可进入 ready set。正常成功路径因此无需为 finalizer 再调用 Planner：
`1×Planner + N×并发 RWKV work + 1×Reviewer + 1×RWKV finalizer`。只有审核后新增了 correction work，
旧 finalizer 不再覆盖全部 work dependency 时，才请求一次 replacement finalizer patch。

强模型输入使用 result capsule，而不是 worker transcript：每个 observation 只暴露 node/status、精确
operation result、当前 artifact hash/revision、错误类型，以及 `replan_applied` 这类已提交控制结果。
不发送 operation arguments、RWKV prompt/transcript、候选自然语言总结、重试/拒绝过程和内部状态。

### 3. Deterministic Scheduler + RWKV Worker Pool

调度器从 DAG 选择所有依赖满足且 scope 不冲突的 ready nodes：

- 所有 atom（包括 exclusive）都使用独立 workspace snapshot；exclusive atom 单独调度，只有完整成功后
  才以带恢复备份的全快照事务替换 parent workspace。失败、超时、中断或进程丢失时，`run_command`
  的任何间接文件副作用都只留在隔离快照；
- 只暴露被 Planner 选中的一个 operation + final_answer；
- 路径 mutation 通常一个 action；显式瞬态恢复可在隔离事务内使用两个 action；read atom 1–4 actions；
  external side effect 独占；
- completed mutation 只合并声明 roots；failed/interrupted snapshot 不合并；
- process-loss 从同一 atom store/snapshot 恢复；
- child actions 带 stage/node/action provenance 投影到父 append-only evidence ledger。

RWKV natural-language summary 永远不是 dependency fact；下游只接收有界 exact observations。修改已有
内容的原子必须直接依赖该目标最新成功的 `read_file/read_json` 节点，使当前内容通过 dependency handoff
进入 RWKV；blind correction writer 在 Planner 语义校验阶段即被拒绝。

### 4. Independent Evidence Reviewer

Reviewer 与 Planner 使用分离 prompt、分离 schema、分离调用：

- 输入为 immutable obligations、未审 evidence delta、artifact revisions 和父 causal events；
- 实际传输为这些事实的 bounded result capsules；不传 RWKV 过程轨迹；
- 对每条 obligation 输出 `satisfied / contradicted / insufficient`；
- satisfied 必须给出 evidence refs；contradicted 必须给出冲突 refs；
- Reviewer 不能创建 atom、执行工具、改写 artifact 或 RWKV Final；
- insufficient 形成 typed evidence gaps，再交给 Planner 生成 graph patch。

Reviewer 后还有一个无模型、只否决的 deterministic evidence kernel：它只计算请求明确要求的机械事实，
例如相对扫描根路径、UTF-8 `line_count`/`byte_count`、`total_files`/`total_bytes`。它不能把任何义务改成
satisfied，只能否决与公开 result capsule 算术矛盾的 satisfied，且永不读取 hidden acceptance。

只有本地 validator 确认所有 execution-evidence obligations 均 satisfied、无 contradiction、引用的 evidence
均存在且属于当前 artifact revision，控制器才调度一个 RWKV finalizer。Finalizer 的依赖必须覆盖每一个
已完成 work node，因此联网证据等只存在 child outcome 的事实也会通过有界 dependency handoff 到达它；新增
correction work 会机械失效旧 finalizer，并要求 replacement finalizer 覆盖新的完整依赖集。

Finalizer 输出原始 Final 后，控制器把该文本原样封装为 content-addressed `final_answer` capsule，再由独立
Reviewer 只审核 `FINAL_PRESENTATION` obligations，并可同时引用已经验收的 execution capsules。只有这次
审核也全部 satisfied 才能写入 `run_completed`；contradicted/insufficient 会请求新的 read-only replacement
finalizer。Reviewer 和控制器都不排序、不替换、不润色、不截断 RWKV 原始 Final。

## 控制流

```text
immutable request
      |
      v
GPT Planner: compile obligations + initial graph patch
      |
      v
deterministic ready-node scheduler
      |
      +----> RWKV atom pool (parallel, scoped, transactional)
                         |
                         v
                exact evidence ledger
                         |
                         v
GPT Reviewer: obligation verdicts + evidence refs
      | satisfied all                    | gaps / contradiction
      v                                  v
RWKV finalizer                    GPT Planner: append patch
      |                                  |
      v                                  |
final-presentation Reviewer              |
      | satisfied / rejected-------------+
      +---------- exact raw Final
```

## 预算与终止

- 不再使用“最多 N 个自然语言 stages”作为主终止条件。
- 使用 `max_graph_patches`、`max_atom_attempts`、`max_reviewer_rounds` 和每义务 retry budget。
- 一个 review round 没有新增 satisfied obligation、artifact revision 或 evidence ref 时，判定 stagnant；
  Planner 只能追加不同 operation/evidence path 的 patch，否则 fail-closed。
- GPT 请求跨 case 有界串行；RWKV case 与 atom 并发保持高并发，两种资源预算彻底分离。
- Planner 可首尝试 medium reasoning；兼容网关返回 5xx 时，同一 logical call 的下一 physical attempt
  自动降为 low，而不是重复三次相同高负载请求。Reviewer 保持独立 medium reasoning。
- 常规题目标 API 量为 1 次初始 Planner + 1 次批量 Reviewer；只有 evidence gap、contradiction 或真实
  worker failure 才调用增量 Planner/Reviewer，不按 atom 或 stage 固定调用。

## Round148 问题映射

| Round148 问题 | Contract Graph 处理 |
| --- | --- |
| 16 个 FP | Reviewer 逐义务引用 exact evidence；Planner 无接受权 |
| finalizer 零 action/stage churn | 全义务关闭后才生成一次 finalizer；过早 Final 在同 atom 重试 |
| 19 个 stage budget exhausted | 改为 obligation progress 与节点预算 |
| 9 个 GPT HTTP 500 | GPT 跨 case限流；Planner 5xx 自动 medium→low；RWKV 并发不受影响 |
| workflow event 缺失 | child action 事实进入父 evidence ledger |
| natural-language summary 污染 | summary 不可作为 evidence/dependency value |
| post-effect crash 被吞 | process-loss 穿透并恢复同一 atom snapshot |
| move/mock_api scope 不匹配 | path mutation 与 exclusive external effect 分离 |

## 不变量

1. 原始 request 是唯一业务 authority；Planner patch 只能引用，不能覆盖。
2. GPT 永远没有 Harness authority；工具执行数必须为 0。
3. RWKV 是唯一 operation 参数、执行与 Final 主体。
4. Candidate summary 不能关闭 obligation；只有注册 evidence ref 可以。
5. Reviewer 不能规划，Planner 不能审核，控制器不能推导业务答案。
6. failed/interrupted snapshot 永不合并；exclusive 的未声明间接写入也只能在完整成功后事务提交；所有父事实可从 child trace 复核。
7. hidden acceptance 永不进入 Planner、Reviewer、RWKV 或运行时 ledger。
8. deterministic kernel 只能否决，不能接受；机械关系与强模型语义审核职责分离。
9. `run_completed` 必须同时绑定当前 execution review 与（存在该类义务时）当前 final-presentation review。

## 当前实验状态（截至 Round156）

- Round155 固定 13 例：TP=4、FP=3、FN=0、OTHER=6；logical GPT=37（中位数 2），比
  Round154 的 50 次更低，但质量门 `>=11/13` 未通过，因此没有启动 Full90。
- Round156 定向 5 例：0 TP、2 FP、1 FN、2 OTHER；它验证了 medium→low fallback 消除了全部
  `contract_plan_unavailable`，且 M10 的 `replan_applied` 使 external acceptance 通过；同时暴露出
  obligation 后续膨胀、机械路径/计数误判和 blind correction writer 三个根因。
- Round157 定向3例为 TP=1、FP=1、FN=1：M10 已恢复严格 TP；M15 的最终 artifact external=true，
  但 stale mechanical evidence 造成 FN；LH06 的未显式 JSON schema 仍造成 FP。
- stale artifact veto 与零 action work atom 已继续离线修正，最终通过 159 个本地测试，但尚未在线复验；
  当前架构不能宣称达到 Full90 晋级条件。
