# Round118 v17 Causal Event Authority + Selected-Schema Feedback 预注册协议

## 决策来源

Round117 v15-B Basic30 为 Strict/External `20/30`、Agent completed `28/30`、FP `8`、
FN `0`，固定 40 项 missing-zero artifact similarity 为 `0.902448750446`。它相对
Round116 的 `8/30` 明显恢复，但低于 Round46 Basic30 的 `24/30`、FP `1`、FN `0`。

Round117 人工逐题审计发现两个全局结构问题：

1. 140 个已执行 Action 在最终 `RunState.actions` 中全部仍为 `running/result=null`，正确
   ActionResult 只存在于 ModelEvent Observation。原因是 `action_started` 持久化深拷贝后，
   Controller 继续修改旧局部 `ActionRecord`。当前 `CausalEnvelope` 只是旁路副本，不是
   权威事实源。
2. B16/B17 在 list 成功后分别连续 12 次输出 `read_file(max_start_byte=...)`；总计 24 次
   相同参数拒绝。RWKV 已选择 `read_file`，但最近的错误 Observation 没有携带这个已选
   operation 的精确 schema。

## 结构变量 A：唯一 append-only 因果事件权威源

运行 schema 升级为 v17。所有持久化阶段只提交统一 `CausalEventDraft`，Store 追加不可变
`CausalEvent`：

```text
schema_version / event_id / run_id / sequence / parent_id / cause_id /
subject_id / event_type / payload_schema / payload / digest / created_at
```

固定要求：

1. `event_type` 必须来自显式注册表，并绑定唯一 `payload_schema`；禁止按事件名字符串前缀
   猜 kind。
2. Action 生命周期使用 `action_started.v1` 与 `action_finished.v1` 两个事件。started payload
   保存模型已提交的完整 Action；finished payload 保存完整 ActionResult、artifact 与 revision。
   不回头修改已持久化对象。
3. `actions/artifacts/artifact_revisions/failure_budgets/active_action/next_sequence` 是对事件链的
   确定性投影。SQLite index、UI、runner 和恢复逻辑只消费投影；投影不得成为第二事实源。
4. 模型调用决定、ModelEvent、rollover、protocol rejection 和 Final 的原始记录进入相同事件
   payload。Model checkpoint/transcript 仅是可重建或校验的 transport cache，不是业务事实。
5. Store 保存前追加事件并重建投影；加载时重新 fold 事件、校验 parent/sequence/digest 和
   projection digest。外部传入的旧 projection 字段不得覆盖事件事实。
6. v16 与更早状态不静默迁移；当前分支只有 v17 在线结构。

## 模型可见变量 B：已选 operation 的精确 schema 反馈

只在 RWKV 已经输出一个已注册 operation、但其参数未通过 Harness schema 时：

- protocol rejection Observation 原样包含错误文本；
- 同时包含 `selected_operation` 和该 operation 当前注册的完整精确 schema；
- schema 放在最近事件中返回同一 RWKV session；
- Controller 不选择 operation，不补、删、改参数，不执行被拒调用，不推断用户意图。

JSON 解析失败、未显示 operation 或无法确定 operation 时不添加猜测 schema。简单 call
envelope 转换范围保持 Round117 不变，不新增 `max_start_byte/max_entries/max_bytes` 业务别名。

## 明确禁止

- 不恢复 Goal parse、Task DAG、`lh_task_call`、selector、reviewer 或 completion gate。
- 不使用隐藏验收、参考答案、文件名或题号影响模型调用。
- 不把 `max_start_byte` 猜成 `start_byte/max_tokens`，不丢弃未知显式字段。
- 不改写 RWKV Final，不增加第二模型或 semantic resampling。
- 不同时加入 scratchpad、mutation verification 提示、repeat guard、workset 或效率优化。

## 离线验收

必须全部满足后才能在线运行：

1. 已执行成功/失败 Action reload 后 status/result 与 exact ActionResult 一致。
2. Action started 后 crash：幂等 Action 只恢复同一 action id；非幂等 Action 不重放。
3. artifact revision、failure budget、pending Observation、UI/runner projection 与事件 fold 一致。
4. 任意 causal event payload/parent/sequence/digest 损坏均拒绝加载；projection 字段篡改不能
   改变权威事件结果。
5. 未知 event type/payload schema 拒绝；每次 revision 恰好追加一个事件。
6. 已选 registered operation 参数错误时，下一 prompt 含精确 selected schema；未解析或未注册
   operation 不含猜测 schema。
7. direct Harness tool、sandbox、uv Python、Final raw equality、rollover 和 Web UI 回归通过。
8. pytest、统一 controller、E2E catalog `90/90`、compileall 和 diff check 全部通过。

## 固定在线数据与顺序

模型、endpoint 与 sampling 沿用 Round117：

- model：`rwkv7-g1i-13.3b-20260805-ctx16384`
- endpoint：`http://127.0.0.1:29610/v1`
- temperature `0.05`、top-p `1.0`、top-k `0`、penalties 不变
- max-transitions `200`、concurrency `1`
- WSL `UbuntuRecovered`、uv `0.12.5`

Stage A 固定 7 题，顺序：`B16,B17,B02,B06,B07,B19,B28`。只要没有状态完整性失败、进程
泄漏或无法生成 Final，即继续 Stage B；Stage A 质量只作诊断，不用于挑选源码。

Stage B 固定 `B01..B30`，顺序不变。无论 Stage A 的单题得分如何，只使用同一冻结源码运行
一次 official Basic30；不得根据 canary 改 prompt 或代码。

## Stage B 门槛

- Strict/External `>=24/30`
- FP `<=1`、FN `<=1`
- 保留 Round46 至少 `23/24` 个 Basic TP
- 固定 40 项 missing-zero similarity `>=0.959895851803`
- B16/B17 不再因同一未知参数连续耗尽 12 次拒绝
- Final 非空/raw equality `30/30`
- 每题最终 Action projection 中不得存在无 finish 事件的 running Action；正常结束题必须
  Action status/result 完整

门槛未通过则不运行 confirmatory、collection 或 full90。通过后才以相同源码、数据、顺序
和参数运行一次 confirmatory。

## 冻结与分析

离线验收完成后、第一次模型请求前生成只读保护的 source manifest。在线运行结束后逐文件
复核。结果必须记录 Strict/External/FP/FN、similarity、请求/Action/拒绝数、B16/B17 精确
链、全部 30 题首次偏离和 causal/projection 完整性；不以单元测试代替能力结论。
