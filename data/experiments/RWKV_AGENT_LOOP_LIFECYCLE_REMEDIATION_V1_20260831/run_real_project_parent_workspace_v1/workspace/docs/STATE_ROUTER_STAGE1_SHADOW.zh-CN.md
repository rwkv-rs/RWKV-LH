# State Router 阶段 1：Shadow 模式

阶段 1 的旁路基础设施和固定 canary 已完成，但分类 canary 未通过，因此当前状态是：

```text
Shadow 基础设施：完成
固定 8 条真实 Controller canary：完成
Stage 1 正式毕业：未通过
Stage 2 建议模式：禁止进入
```

Router 使用本地 `/home/chase/GitHub/vllm-rwkv` 的 0.4B RWKV，不使用其他推理引擎。入选
方案仍是阶段 0 的最后一层 WKV stats、train-only PCA 和多头 MLP；模型、PCA、head、阈值和
解析协议都没有依据 Shadow 结果重新训练或校准。

## 接入边界

CLI、Web Worker 和主动任务都从 `build_product_controller()` 构造同一个产品 Controller。
只有不可变 Goal policy 显式包含以下对象时才包裹 `run()/resume()`：

```json
{
  "state_router": {
    "schema_version": "rwkv-lh.state-router-runtime-policy.v1",
    "mode": "shadow"
  }
}
```

默认仍为关闭，关闭时 runtime policy 不增加 `state_router` 字段，Controller 对象也不包裹。
Shadow 在 Controller 调用前运行本地 Router，调用后从 Action Ledger 与 Harness capability
metadata 投影实际行为。该行为只用于比较，并明确标记为 `not_ground_truth`。

每个 run 写入独立的 `state_router_shadow/run-<run-id-sha256-prefix>.jsonl`：

- prediction：机械 Router input、分类、置信度、artifact hash 和调用前工具菜单摘要；
- outcome：operation/family/status、联网尝试、调用后菜单摘要和非真值 agreement；
- error：Router/校验/日志失败；失败不会改变 Controller 返回或异常；
- 每条记录都有独立 digest、`shadow_only=true` 和全部 `influence=false`；
- 不写工具结果正文、环境变量或认证信息，也不写 Controller causal chain。

Shadow 不向 13.3B 主模型加入 prior，不调整工具顺序，不选择 State Profile，不改变工具参数、
Network Gate、Contract Graph、验证器或完成判定。

## 使用

CLI 新 run：

```bash
uv run rwkv-lh --state-directory data/runs start \
  --request "读取 input.txt 并返回内容" \
  --workspace /absolute/scoped/workspace \
  --state-router-shadow
```

主动任务在 `enqueue` 使用相同的 `--state-router-shadow`。resume 不重新选择模式，而是使用
已持久化的不可变 policy。Web UI 提供“启用 State Router Shadow”复选框和独立 Router
Shadow 标签页；`GET /api/runs/<run-id>/shadow` 支持增量读取。所有项目命令在 WSL
`UbuntuRecovered` 中执行。

## 固定 canary 结果

固定数据为 `rwkv-lh.state-router-shadow-canary.v1`，8 条覆盖 final、local、local mutation、
deterministic、web、connector、mixed 和歧义 OOD。每条都经过真实 13.3B endpoint、产品
Controller、Harness 和本地 0.4B Router。

| 指标 | 结果 | 预注册门槛 | 判定 |
|---|---:|---:|---|
| route accuracy | 0.375（3/8） | ≥0.75 | 失败 |
| network accuracy | 0.875（7/8） | ≥0.875 | 通过 |
| OOD abstain | 1/1 | 1/1 | 通过 |
| 高置信非弃权 route | 2/2 | 只报告 | 样本不足 |
| Router/主行为 agreement | 1/8 | 只报告、非真值 | 不作 accuracy |

逐条 route 为：

| case | 预期 | Router | 主行为（非真值） | Controller |
|---|---|---|---|---|
| 001 | final | final | final | completed |
| 002 | local | abstain（candidate local） | local | completed |
| 003 | local | abstain（candidate connector） | local | completed |
| 004 | deterministic | abstain（candidate deterministic） | deterministic | completed |
| 005 | web | abstain（candidate mixed） | web | completed |
| 006 | connector | abstain（candidate deterministic） | mixed | interrupted |
| 007 | mixed | mixed | connector | interrupted |
| 008 | abstain | abstain | web | completed |

基础设施门槛全部通过：8/8 prediction/outcome 配对、8/8 菜单摘要不变、跨 run 混写 0、
causal-chain Shadow 事件 0、全部 influence false、全部记录 digest 有效、Controller exception 0。

## 失败结论

真实请求相对阶段 0 固定 test 出现明显分布漂移。6/8 输出选择安全弃权；冲突原因覆盖 4 条
context-head 冲突、3 条 phase-head 冲突、2 条 route 置信度不足，以及少量 margin、route/network
冲突。机械 Controller facts 成功阻止冲突分类变成建议，因此没有安全越权，但也使 route
coverage 和准确率无法达到 canary 门槛。

这 8 条不足以评价正式高置信度准确率。按预注册协议，进入阶段 2 前仍需至少 100 条去重、
有人工/机械审核标签的有机 Shadow 轨迹，并重新预注册来源与切分。当前不得用 canary 标签
训练、调阈值或通过反复改写这 8 个请求改善结果。

主行为日志还暴露了独立的主模型问题：web provider 不可用后仍完成、connector 成功后重复
调用触发 egress 拒绝，以及 mixed 用例未先读取本地输入。这些事实不作为 Router 真值，也不由
Shadow 修复；应进入单独预注册的 Controller/Harness 回归。

完整预注册、结果和审计见
[`RESULTS.md`](../data/experiments/STATE_ROUTER_STAGE1_SHADOW_V1_20260827/RESULTS.md)。
