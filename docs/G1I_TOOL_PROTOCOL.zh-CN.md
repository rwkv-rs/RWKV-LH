# G1i 工具协议、state 边界与架构消融

## 1. 当前结论

RWKV-LH 当前使用 `g1i-tool-dialog.v1` 作为实际 Harness 工具调用协议。协议由项目显式渲染并通过 OpenAI-compatible `/completions` 发送，不依赖服务端默认 chat template。

当前 vllm-rwkv 服务虽然启用了原生 tool parser，但固定数据复测中，原生 parser 的工具选择正确率和延迟都不适合作为默认路径。它保留为已探测能力，不与生产 G1i 路径组成双重 parser 或双重 agent 状态机。

当前服务没有暴露 recurrent state 的 create/resume/fork/export/import handle。完整 prompt replay 是正确性 fallback，不等于 RWKV state 复用，也不能用来证明 state 带来的延迟、分支和恢复收益。

## 2. 规范格式

初始调用：

````text
System: Tools: [{"name":"read_file",...}]
Return only a JSON function call.

User: <任务提示>

Assistant: ```json
````

模型生成：

```json
{"name":"read_file","arguments":{"path":"input.txt"}}
```

工具执行后续轮：

````text
User: Function output: {"success":true,"output":"..."}

Assistant: ```json
````

这里的 `User: Function output` 是一个新的 User turn。它不能连续写入前一个 Assistant 块，也不能由 chat template 隐式改写角色或 fence。模型返回 `submit` 只代表终止意图；Controller 仍须检查确定性证据、任务状态和 Goal coverage。

## 3. 模块职责

- `rwkv_lh/tool_protocol.py` 只负责 G1i 字节格式、完整前缀重放和 `{name, arguments}` 归一化。
- `rwkv_lh/model.py` 先选择 action type，再对单一已选工具调用 G1i 协议；它不直接执行工具。
- `rwkv_lh/harness.py` 拥有工具参数契约、相对路径边界、副作用和幂等性不变量，并生成内建动作的确定性后置条件。
- `rwkv_lh/validation.py` 执行后置条件并形成可观察结果，不负责选择动作。
- `rwkv_lh/controller.py` 拥有执行、持久化、重试、replan 和完成边界。

自定义 Harness action 没有内建后置条件映射时，才回退到 RWKV verification design。内建动作不再让模型重复发明可由 action arguments 确定的 verifier 参数。

## 4. 为什么保留两阶段动作物化

本轮消融比较了两种生产接法：

1. 完整 Harness 工具表一次生成 `{name, arguments}`；
2. 先用紧凑 catalog 选择 action type，再把单一工具放入 G1i `System: Tools` 生成 arguments。

一次生成方案不是因为调用更少就更好。固定五题生产链测试中，它只有 3/5 工具名正确；`remove_line` 被改成了保守的 `read_file`，`read_json` 后续又被模型生成的无效 verifier 参数阻断。

单工具方案得到 5/5 工具名正确、5/5 完成、4/5 exact，统一 UTF-8 byte 5-gram cosine 平均相似度为 `0.988121`。唯一非 exact 是根目录写文件的 `create_parents=true/false`，两者对该已存在根目录的可观察结果相同；评价口径和预注册 expected 没有在运行后修改。

因此最终架构保留 action-type 选择。它在这里是控制 RWKV 选择空间的有效边界，不是应按调用数量机械删除的冗余。

## 5. 原生 parser 与显式 G1i 的复测

固定数据集：`data/datasets/rwkv_g1i_online_tool_dialog_v1/cases.json`，五题、工具调用与 Function output 后 submit 两阶段。参数固定为 temperature `0.03`、top-p `1.0`；统一指标为 `utf8-byte-ngram-cosine.v1`、UTF-8 byte 5-gram cosine、near-duplicate 阈值 `0.95`、exact `1.0`。

WSL 重启后的 `vllm_rwkv_native_tool_parser_v2_run3.json` 结果：

| 变体 | 请求 | 工具名正确 | exact | 平均相似度 | 平均延迟 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 显式 G1i `/completions` | 10 | 9 | 4 | 0.715222 | 531.078 ms |
| 原生 default named parser | 10 | 4 | 1 | 0.460848 | 2624.918 ms |
| 原生 + 自定义 G1i template auto | 10 | 0 | 0 | 0 | 2744.680 ms |
| 原生 + 自定义 G1i template named | 10 | 0 | 0 | 0 | 2746.208 ms |

显式 G1i 首轮工具调用为 5/5 工具名正确。两个非 exact 首轮样本只是 `arguments` 被输出为 JSON 字符串；生产归一化后都是 exact。submit 阶段的参数 schema 在该探针中允许任意字段，因此不能把 submit argument exact 当作生产工具参数能力结论。

## 6. 本轮系统性修复

- 接受 object arguments 和 JSON-string arguments，统一归一化后再验证；混合旧 envelope、未知顶层字段和非对象 arguments fail closed。
- 模型工作记忆不再暴露宿主机绝对 workspace root，只暴露逻辑 scope `.`。
- `path`、`source`、`destination`、`cwd` 必须是 workspace-relative；绝对路径在动作执行前拒绝并进入协议纠正。
- `write_file.overwrite=true` 成为幂等重试不变量；G1i schema 用 `const: true` 明确表达。
- 内建动作的 `action_succeeded`、文件内容/存在性、JSON 值、命令退出码和 evidence binding 后置条件由 Harness 确定性生成。
- 自定义动作仍可声明自己的 postcondition，并保留模型 verifier design 扩展边界。

## 7. 数据与复现边界

可提交的固定数据和 JSON 结果位于：

- `data/datasets/rwkv_g1i_online_tool_dialog_v1/`
- `data/experiments/rwkv_lh_architecture_ablation_v1/vllm_rwkv_native_tool_parser_v2_run3.json`
- `data/experiments/rwkv_lh_architecture_ablation_v1/g1i_production_action_validation_run1.json` 至 `run5.json`

`run1` 是完整工具表一次调用反例；`run2` 恢复两阶段选择并移除内建 verifier 生成；`run3` 增加相对路径边界；`run4` 固化 overwrite 幂等不变量；`run5` 使用最终 G1i 参数 schema。

生成这些结果的临时探针只位于项目 `temp/`，必须使用绝对路径在 WSL 执行，不进入 Git。正式单元测试位于 `tests/`，属于产品回归而不是临时探针。

## 8. recurrent state 后续接口

推理端提供真实 state handle 后，协议层应新增：

- create：写入一次 System Tools 与初始 User turn；
- append-and-generate：追加 Function output User turn 和 Assistant fence；
- fork：为验证或备选路径创建只读分支；
- commit/rollback：只提交成功工具结果及证据；
- export/import：服务重启后的 durable snapshot；
- model、shape、dtype、parent digest 校验。

在这些能力实际存在并通过恢复测试之前，代码和文档都不得把 prompt cache、cached token 或完整前缀重放称为 RWKV recurrent state。

## 9. RWKV-E2E-42 全量结果

最终候选代码在同一 WSL、同一 G1i-13.3B、同一 29610 端点上执行了完整 `RWKV-E2E-42`，固定 `max_transitions=200`、隔离 case concurrency `8`。原始汇总位于 `data/experiments/rwkv_lh_architecture_ablation_v1/live_20260811_g1i_protocol_e2e42_run1/results.json`。

| 分组 | 严格通过 |
| --- | ---: |
| basic | 5/10 |
| medium | 0/10 |
| hard | 0/10 |
| long-horizon | 0/12 |
| 合计 | 5/42 |

严格通过题为 `E2E-B02`、`E2E-B04`、`E2E-B06`、`E2E-B07`、`E2E-B10`。这说明本轮 G1i 工具协议整改已进入真实端到端路径，但整个项目仍不能标记为问题解决或生产可用。

全量影响范围显示至少四类剩余系统问题：

- Goal 级 semantic cross-check 仍会错误拒绝成功的中间观察任务；B01 中正确的 `list_directory` 因“目标文件尚未创建”被判失败，证明任务推进与 Goal 满足仍混用。
- failure-analysis、plan 和 replan 的自由 JSON 会膨胀、截断或产生复用 ID、自依赖、错误 replacement 等结构协议失败。
- 少数 G1i completion 输出改成了 `type/function` 原生 wrapper；当前严格规范只接受顶层 `{name, arguments}`，因此 fail closed。是否增加有记录的兼容归一化必须单独预注册并复测，不能静默混用两套协议。
- 部分 run 由 Agent 标为 completed 但外部验收失败，Goal evidence 与真实 observable result 仍未完全分离。

下一阶段的优先级不是继续修改 fence 字符串，而是落实 task-local validation、typed Goal evidence、确定性 replan ID/引用重写、recovery lineage 和 producer-directed correction。真实 recurrent state 接口仍是其后的独立能力层。
