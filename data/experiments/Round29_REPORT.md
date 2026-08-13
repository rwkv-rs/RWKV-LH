# Round29 结构整改与验证报告

日期：2026-08-13。基线提交：`fef3a3b3339d`。当前结果尚未提交或上传。

## 结论

本轮已经把在线执行收敛为一条紧凑主链：

`Task batch → G1i action → ActionResult/metadata → dependency memory → Task postcondition → RWKV provenance criterion commit → final revalidation`

Controller 不生成或修改 RWKV 的 action、criterion、binding、reason、摘要或最终答案。Goal 完成证据只能由
`commit_criterion_evidence` 提交；actual 只能来自当前 Task 的真实观察，expected 只能来自 Immutable Goal 或已完成直接依赖。
Controller 只验证引用覆盖、作用域、digest、依赖关系和工作区 path lineage。

在线 progressive witness、pre-action witness intent 和 `validation.v4` criterion assertion 已从 Controller 决策路径移除。
历史 schema/state 和部分不再被 Controller 调用的 witness helper 仍保留作旧状态读取与离线兼容；后续可做物理删码，但它们不能再生成在线
CriterionEvidence。

## 本轮发现并修复的结构根因

1. Round27/28 的主体 action 链已能正确完成 B02 的读、写和回读，但旧 proof 层需要多轮 schema、operator、source、handle
   绑定，弱模型在这里失败并把正确任务链放大为 Strict 失败。
2. 新协议第一次接入时，最终重验仍不认识 `rwkv_provenance_commit.v1`。现在最终完成前会重新计算 Goal、memory、artifact 和
   workspace digest；来源变化立即使证据失效。
3. crash recovery 能通过 verifier 观察已写文件，却没有当前 Task 的 actual source。现在只读登记
   `workspace_recovery_observation`，不重执行写操作，也不把 verifier expected 参数混入实际观察。
4. 31 文件验收第一次暴露严重假阳性：系统实际读完 31 个文件，但 Goal capsule 在压缩时只保留最后 1 条 read observation；
   随后只建立 1 个 summary 仍能完成 Goal。根因是 full file body、artifact、详细 Task 和 observation 在同一 5K capsule 竞争。
5. 修复后 Goal capsule 保留全部紧凑 action observation（path、cursor、completion metadata），不重复文件正文；完整正文继续保存在
   各 Task dependency memory 中，由对应文件的后续 action proposal 独占读取。64 个 Task 的紧凑结构索引也不会被压缩掉。
6. 大型 fan-out 改为最多 8 个立即可执行 Task 一批。此约束同时在 Model adapter 和 Controller 信任边界验证，自定义模型不能绕过。

## 大型代码项目结构验收

固定验收使用 31 个独立 Python 文件，执行：

`list_directory → 4 批并行 read（8/8/8/7）→ 4 批 per-file summary（8/8/8/7）→ aggregate`

验收确认：

- 31 个目录成员全部来自真实 list observation；
- 31 个 read observation 全部保留在紧凑 Goal capsule；
- Goal capsule 不携带 read 正文，避免上下文随项目线性膨胀；
- 每个 summary Task 从自己的 read dependency memory 读取正文；
- aggregate 依赖全部 31 个 summary Task，输出覆盖全部文件；
- 观察到 8 路 read-only parallel frontier；
- 没有出现“只总结部分文件却完成 Goal”的假阳性。

这是结构验收，使用确定性 fixture 隔离 Controller 行为；它不等价于真实 RWKV 已完成 31 文件语义总结。

## 验证结果

- 完整 pytest：格式边界 v2 后为 `317 passed in 31.36s`（此前结构冻结点为 `302 passed in 187.31s`）。
- LH-Control-30：`30/30`，结果见 `Round29_final_verified/lh_control_30/`。
- E2E-90 validate-only：`90/90` catalog valid。
- provenance 边界：缺失、重复、未知、越权、同路径 actual/expected 均 fail closed。
- provenance 恢复：workspace 内容变化会在 final revalidation 中使 CriterionEvidence invalidated。
- 协议边界：显式 `action`、`tool` 和单 `tool_calls` envelope 只做透明归一化，raw/normalized payload 可审计；不补 action 或参数。
- 格式边界全量回放：Round22 的 579 次冻结 tool response 中 `562` 次可进入真实 action contract，接受后源工具名/参数
  不一致为 `0`；新恢复的 10 次只把无歧义平铺参数整体搬入 `arguments`。剩余 17 次为 12 次工具选择冲突、4 次字段
  冲突/混入元数据和 1 次不完整 JSON，均未放行。详见 `Round29_format_boundary_replay/`。
- 读取边界：目录和 UTF-8 文件分页可无重复、无丢失地重建；cursor/offset 只来自前一页 metadata。
- 并行边界：仅 `read_only=true && side_effect=false` 的 action 并发；worker 使用隔离 RunState，SQLite 合并串行且顺序稳定。
- 因果审计：正式 runner 新增 `causal_ledger.json`。它不聚合语义结论，而是以稳定 ID 关联完整 prompt、raw output、
  parsed/normalized protocol event、event/revision、字段 delta、Task dependency、Attempt、Memory、Artifact、CriterionClaim 和
  CriterionEvidence；原始 `model_trace.json`、`event_log.json`、`state_timeline.json` 继续保留并以 SHA256 互相校验。

## 未完成与上传判断

固定 Round29 E2E-B02 真实 canary 未运行。`scripts/runtime_smoke.py` 在 2026-08-13 检查配置的
`http://127.0.0.1:29610/v1`，结果为 connection refused。因此本报告不声明 Strict E2E 提升，也不把离线 fixture 结果冒充
RWKV 模型结果。

按照“只有更好才上传”的约束，当前不提交、不推送。恢复本地 RWKV endpoint 后，下一步必须先跑固定 E2E-B02；若 Strict、
证据生成和请求链通过，再跑 31 文件真实 RWKV 验收，最后才决定提交与上传。
