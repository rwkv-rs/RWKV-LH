# G1J 全 zero State 分阶段格式冻结结果 V1

时间：2026-09-02（Asia/Shanghai）

## 结论

在固定样本、固定 zero State、固定采样参数、固定停止串和固定角色校验器下，生产格式按角色冻结如下：

| 环节 | 冻结输入边界 | 样本 | 归一化解析 | 正确 operation | 角色语义 | 参数逐值保持 |
|---|---|---:|---:|---:|---:|---:|
| Selector Intent | 2.9B hidden feature + 已登记 Head；不生成文本 | 32 | 不适用 | 32/32 | 32/32 | 不适用 |
| Executor Args | `ExecutorArgsPromptV1` 后接 `**Tool Call:**` 与预开 `json` 围栏 | 32 | 32/32 | 32/32 | 32/32 | 32/32 |
| Step Auditor | 原完整生产模板与原 `Assistant: ```json` 边界 | 32 | 32/32 | 32/32 | 30/32 | 32/32 |
| Finalizer Answer | 原完整生产模板、原 JSON 边界、生产输出预算 | 28 | 28/28 | 28/28 | 28/28 | 28/28 |
| Final Auditor | 显式终局六字段简洁合同，后接 `**Tool Call:**` 与预开 `json` 围栏 | 32 | 32/32 | 32/32 | 32/32 | 32/32 |

对应扫描变体分别为：

- Executor Args：`current_production_full_tool_call_json_open_production_limit`
- Step Auditor：`current_production_full`
- Finalizer Answer：`current_production_full_production_limit`
- Final Auditor：`current_production_full_explicit_final_concise_tool_call_production_limit`

## Step Auditor 决策

不修改当前 Step Auditor 提示词。原模板的归一化解析率为 100%，完整角色语义为 93.75%（30/32）。三种针对两条漏写 `step_id` 的修订均更差：

- 显式六字段版本使多数输出退化为无 function envelope 的裸 decision 对象；接受它将要求控制器推断 operation，超出纯归一化边界。
- `step_id const` 版本完整角色语义为 78.125%（25/32）。
- 最小 step 绑定版本归一化解析与角色语义均为 90.625%（29/32）。

因此保留原模板，并把 2/32 的缺字段输出作为真实 zero-State 基线失败；转换层不得补写 `step_id`。

## 归一化边界

冻结的输出归一化版本为 `direct-call-envelope.v3`。它只允许：

1. 去除输出首尾空白；
2. 去除完整闭合的 plain/json Markdown 外围围栏；
3. 把模型实际产生的调用信封（例如 `name/arguments`）映射为内部 `function/params`；
4. 当 `arguments` 本身是一个 JSON 字符串时，将它解码为同一个 JSON 对象。

它明确禁止：

- 新增、删除或重命名任何工具参数字段；
- 修改字符串、数字、布尔、null、数组或嵌套对象的值；
- 注入默认值、修复缺字段、推断 operation 或改写角色语义；
- 把协议拒绝当成 Goal 停止；
- 把 Finalizer 的 `final_answer` 候选直接当成完成。只有 Final Auditor 输出合法 `ready_for_final` 后 Goal 才能停止。

原始模型输出、输入信封、归一化信封、转换轨迹和两侧摘要均进入运行审计。格式不合法或角色语义不合法时失败关闭，不进行语义重采样。

## 扫描规模与完整性

- 13.3B 文本生成最终记录：1312 条，42 个固定角色/变体/样本组合，无传输错误。
- Selector Head：32 条，准确率 100%，未生成 RWKV 文本。
- `generation_records.jsonl` SHA-256：`877de770aa7c35a2684561fe4fdbc0ee0f6ebd63e0d8111cb51bff5fd6b7357a`
- `selector_records.jsonl` SHA-256：`9ed3d8f0d5a585311aa9ab039ce1925fdf163f3bdaf684f80aa6b0fa12a3a7ef`
- `NORMALIZED_FORMAT_SCAN.json` SHA-256：`cb449a56258452784ae79da87d073c0a6adb9bdaaad514b036858f05c9fce369`

## 验证

相关代码回归：

```text
95 passed in 36.37s
```

覆盖输出信封归一化、字符串化 arguments 的深层逐值保持、各角色生产提示、独立 Selector/Executor 网络接入和真实 Goal 生命周期。未执行任何 Head 训练或 StateTune。

## 能力基线边界

本结果只冻结输入输出协议，不计入 B01–B14 或 P01–P07 能力得分。真实 Agent 基线仍必须实际创建/读取/验证工程产物，并保存完整工具结果与 Goal 审计链；任何 Supervisor 429 或隧道中断单列为基础设施无效，不得计作模型能力失败或成功。
