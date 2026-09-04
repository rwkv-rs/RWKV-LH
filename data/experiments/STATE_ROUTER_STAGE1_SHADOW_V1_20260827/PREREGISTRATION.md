# RWKV-LH State Router 阶段 1 Shadow 预注册

- 日期：2026-08-27
- 状态：实现和 canary 运行前冻结
- 阶段边界：Router 读取真实 Controller 请求并记录预测；不得影响主模型、工具菜单、参数、
  Network Gate、Contract Graph、State Profile 或完成判定。

## 固定 Router

- 引擎：`/home/chase/GitHub/vllm-rwkv@67f0c5996c50dca0ad779da545cb491527de988f`，要求 clean。
- 候选：阶段 0 入选的 B，最后一层 WKV stats + train-only PCA + 多头 MLP。
- 模型 manifest SHA-256：
  `670e2229b209c21b13a9671b62d9161f2e507bbff0429a24575e14cef43da541`。
- Head 文件 SHA-256：
  `722504bf83089099ae3ca77ebe28df63d5a7d5b19a48ee8891c50536ac683109`；
  head hash：`7dc131ffe98e65e074e41637f1b1c49ffdc45c4b6288ba7f574dcc64ec540f10`。
- PCA 文件 SHA-256：
  `42d421d98134b0e4ab8071f4ac54d814a887a80649b1c13a7412db5dac0a2120`；
  projection digest：`189e2b550cdd2c577280cc2456dddc1eb98ba45d4c31e57231014327386409df`。
- Stage-0 阈值、模型、PCA、head 和输出解析全部冻结；Shadow 不允许重新训练或校准。

## 输入机械投影

- 新 run：`mode=fresh`、`summary=null`、`EvidenceState=none`。
- resume/已有状态：`mode=continuation`；Summary 只包含状态、action 计数和 operation 名，
  不包含工具输出，不成为机械真值。
- EvidenceState：Controller 已完成为 committed；存在 active/succeeded action 为 partial；
  其余 continuation 为 missing。
- PolicyState：immutable retrieval policy 为 `offline` 时 denied，其余模式 allowed。
- `trace_id` 同时绑定 run ID、调用前 revision 和唯一 invocation ID。

## 旁路与失败规则

1. 唯一接入点是 CLI、Web Worker、主动任务共享的 `build_product_controller()`。
2. 默认关闭；仅 immutable runtime policy 显式选择 `state_router.mode=shadow` 时启用。
3. Controller/Harness/Model 实例不被替换或修改；Shadow 只包裹 `run()/resume()` 返回边界。
4. 预测在 Controller 调用前写入独立 JSONL，结果后写入 outcome；不写 causal chain。
5. Router 加载、CUDA、hash 或日志错误必须记录为 Shadow error 并让 Controller 原样继续。
6. 实际行为从 Action Ledger 和 Harness capability metadata 投影；它是比较对象，不是真值。
7. 每条记录必须声明 `shadow_only=true` 和全部 `influence=false`。
8. 每个 run 使用独立日志文件；追加写加文件锁并 `fsync`，禁止跨 run 混写。
9. 日志不得包含工具结果正文、环境变量或认证信息。
10. Shadow 禁止改变 G1i 工具定义及顺序；调用前后记录 tool-menu digest。

## 固定 canary

- 数据：`rwkv-lh.state-router-shadow-canary.v1`，8 条；cases SHA-256：
  `cf650d5c2af0011012c0d88780efc597c90ff392542e9b313d99408911426d53`。
- 每条通过真实 13.3B RWKV endpoint、Controller、Harness 和本地 Shadow Router 执行。
- 固定覆盖 final/local/local-mutation/deterministic/web/connector/mixed/OOD。
- canary 分类门槛：route accuracy `>=0.75`、network accuracy `>=0.875`、OOD abstain `1/1`。
- 基础设施门槛：8/8 均有 prediction/outcome 或 prediction/error 配对；Shadow error 不终止
  Controller；tool-menu digest 前后相同；跨 run 混写 `0`；输出影响字段全部为 false。
- 主模型 action 与 Router route 的 agreement 只报告，不作为 accuracy，也不得据此改 canary 标签。

## Shadow 正式毕业门槛

本次固定 canary 不能替代真实流量。进入阶段 2 前还必须积累至少 100 条去重、有人工/机械审核
标签的有机 Shadow 轨迹，并重新预注册其来源与切分；高置信 route accuracy `>=0.98`、OOD
abstain recall `>=0.90`、错误且未 abstain `<=0.02`，且无新增 P1/P2、无 Network Gate 或菜单
差异。未满足时，阶段 1 只能标记为“基础设施/canary 完成”，不能标记正式毕业。
