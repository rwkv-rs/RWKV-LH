# Round5 线性 Typed Assertion 专项分析

本分析只在 90 题全部结束后执行。隐藏 acceptance 与冻结 Codex 标准答案不参与 RWKV 请求、assertion
生成、透明归一化或 proof 求值。

## 结论

`linear_typed_criterion_assertion.v1` 改善了顶层 validation 合同形成率和 External，但没有解决弱 RWKV 对
“联合枚举 + 全可选字段”示意合同的照抄问题。58 个 assertion attempt 中有 40 个顶层合同有效，模型共给出
55 条 assertion；然而 `0/55` 能进入无损归一化，proof pass `0/58`，CriterionEvidence 为 0，最终 Agent
completed `0/90`。

固定 E2E 指标：External `12/90`、Strict `0/90`、Agent completed `0/90`、FP `0`、FN `12`。难度组
External 为 Basic `9/30`、Medium `2/30`、Hard `1/30`。FP=0 是全无 completion 的空洞安全结果。

## Validation 与 assertion 数据

| 指标 | Round4 recursive DSL | Round5 linear typed |
| --- | ---: | ---: |
| 进入 validation 的题 | 26 | 28 |
| validation 请求 | 132 | 76 |
| assertion/claim attempt | 84 | 58 |
| 顶层合同有效 attempt | 38 | 40 |
| 顶层合同无效 attempt | 46 | 18 |
| contract error event | 93 | 36 |
| RWKV pass / replan event | 34 / 50 | 40 / 18 |
| 实际 assertion/claim | 55 | 55 |
| verified | 0 | 0 |

Round5 的顶层有效率从 `38/84` 提高到 `40/58`，但 55 条线性 assertion 全在无损归一化前被拒绝：

| 首个拒绝类别 | 条数 | 占 55 条 |
| --- | ---: | ---: |
| source 不相容字段 | 39 | 70.91% |
| 把联合枚举/占位符当作 source 值 | 12 | 21.82% |
| 自创字段 | 4 | 7.27% |

典型原始输出包括：

- `source: "workspace|action_result"`，即逐字复制合同里的联合枚举；
- workspace 同时带 `task_id/artifact_id/memory_id`，或 action_result 同时带 `path`；
- selector 自创 `file_content/json_field_equals/file_exists`；
- transform 自创 `read/read_file/read_json`，或逐字复制全部 transform 枚举；
- 预期侧仍有 workspace 11 条、action_result 9 条和联合 mutable source 4 条。

因此不能通过“删除 null/多余字段”或把联合字符串拆成候选再选一个来提高通过率：这既不是透明归一化，也会
掩盖 expected source、selector、transform 与 comparison 的真实语义错误。

## 外部正确但没有 Goal evidence

12 个 FN 为：`B02/B04/B13/B14/B17/B22/B26/B29/B30/H04/M18/M21`。

- B02/B04/B13/B26/B29/B30/H04/M18 有 RWKV pass assertion，但全被上述形态边界拒绝；
- B14/B17/B22/M21 的 assertion event 只有 fail-closed replan/空 assertions；
- 所有 12 题 CriterionEvidence 都是 0，控制器没有读取 hidden acceptance 来补证据。

## 单调用复用的真实结论

Round5 的 58 个 attempt 全是 optional `criterion_cross_check`；没有模型计划显式
`model_cross_check`，所以预注册的“显式检查复用同一决定”路径本轮触发 0 次。没有 attempt 发生重复
assertion cross-check，但请求下降不能归因于该复用逻辑。76 个请求与 58 个 attempt 的差额来自 validation
合同纠正调用；Round4 也同样主要是合同纠正，而不是两个 semantic validator 串联。

## 下一步约束

下一轮可以继续借鉴 Prime Agent/弱模型工具协议中的 progressive disclosure：把 source+selector 合并成
RWKV 明确选择的具体只读 operator，并给每个 operator 独立、无占位联合值的参数合同。运行时只能逐字映射
RWKV 选定的 operator/参数/transform/comparison，不得依据 Goal、hidden acceptance 或实际文件内容替它
选择 operator，也不得删除字段、尝试候选或修改 final answer。

机器明细见 `linear_assertion_analysis.json`。
