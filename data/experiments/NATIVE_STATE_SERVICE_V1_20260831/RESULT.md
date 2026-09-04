# 13.3B 原生 RWKV state 服务结果

日期：2026-08-31

## 结论

本地 vLLM-RWKV 推理引擎已经补齐并部署到 13.3B 生产服务。当前本地入口为
`http://127.0.0.1:29613/v1`，服务名保持
`rwkv7-g1i-13.3b-exe-g3-g6-deterministic-cmix-r7-multiprofile-ctx2496`，现有客户端无需改模型名。

`GET /v1/capabilities` 返回完整 `rwkv-lh.native-state.v1`：create/resume/fork/commit/rollback/
export/import 全部为 true，`prompt_replay=false`。WKV state 固定为
`cache_role=disposable_acceleration`、`authoritative=false`，不能直接授权 Action、完成 Goal 或替代
Goal/CausalEvent/Action 权威事实。

## 系统整改

- 推理服务增加 `/v1/capabilities` 与 `/v1/state/create|append|fork|generate|commit|rollback|import`；
- recurrent tensor state 以 state ref 传递，正常后继只消费 parent state + 新 token delta；
- candidate 在校验通过后 commit，拒绝时 rollback；pending token 边界固定为
  `state_before_exactly_one_pending_token`；
- serving 层在流结束前完成 candidate capture，并能用唯一 target state ref 解析 vLLM 内部规范化后的
  request id；
- RWKV `/tokenize` 在 `add_special_tokens=false` 时不再重新注入仅供引擎使用的 BOS，使 one-shot 与
  state+delta 使用完全相同的 token 序列；
- cache binding 覆盖 lane、model、profile、state chain、delta、event 和 parent digest；错误
  model、authority 或 parent binding 均 fail closed；
- 产品 session 由 capability 工厂选择 `native_rwkv`；`native_required` 不会静默退回 prompt replay。

## 固定验收

数据集：`data/datasets/rwkv_lh_native_state_service_v1/cases.json`，版本 `2026-08-31.v1`，4 例，
SHA256 `6c70182e6aa5566cf983fe3af0811fb4e2d87aaee4e7199d67ec0de19eb5f569`。

| 指标 | 分数 | 阈值 |
|---|---:|---:|
| capability exact accuracy | 1.0 | 1.0 |
| continuation token exact accuracy | 1.0 | 1.0 |
| lifecycle exact accuracy | 1.0 | 1.0 |

生命周期覆盖 candidate rollback、commit/export、显式 import、导入后续写 token 一致、容量 16 的
cache 淘汰压力后恢复，以及错误 model/authority/parent binding 拒绝。完整逐调用结果见
`PRODUCTION_RESULT.json`。

产品客户端另行使用 `native_required` 实测：transport 为 `native_rwkv`、
`prompt_replay=false`、rollback 后父 state ref/digest 精确恢复。13.3B 原始输出为显式
`list_directory` 调用；候选 commit 后，Harness 直接在 `/home/chase/GitHub/RWKV-LH` 母路径执行
只读 Action，确认关键项目入口存在、受保护源码摘要不变，再把 ActionResult 作为新 delta 追加到
child WKV state。结果见 `PRODUCT_CLIENT_PRODUCTION_RESULT.json`。

## 代码回归与真实项目边界

- RWKV-LH state/runtime/controller 定向测试：113 passed；
- vLLM-RWKV 原生 state 与 tokenizer 定向测试：11 passed；
- RWKV-LH 完整 suite：729 passed，1 个 Python 3.13 `fork()` 弃用 warning；
- 真实 RWKV-LH 项目副本直接作为 `Goal.workspace_root` 的固定 Harness 验收：23/23，覆盖 14 个
  实际 Action 和失败恢复。该结果位于
  `../RWKV_AGENT_LOOP_LIFECYCLE_REMEDIATION_V1_20260831/run_real_project_parent_workspace_v1/RESULT.json`。

生产 state transport 通过不等于多步模型能力达标。固定三题 Agent canary 的 0/3 结论未被改写；
后续模型能力实验仍必须使用固定数据、参数、阈值和 verifier。

部署身份、源码逐文件 SHA、模型/profile/build 与运行开关见 `DEPLOYMENT_MANIFEST.json`。
