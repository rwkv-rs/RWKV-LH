# G1J 2.9B Selector zero-State 开发集审计

日期：2026-09-01

## 结论

本轮失败不是 `PlanPatch`、JSON 解析或响应格式不匹配。最早可直接证实的失败发生在 Selector 分类结果：`selected` 与固定标签 `label` 不一致。

更上游的工程原因也已定位：S60/V7 输入把完整多步骤 Goal 放在最后一个语义字段 `current_question.complete_requirement`，而 Strong Planner 的当前 frontier 只能放在更靠前的 `current_question.current_stage`。这要求 2.9B 重新从完整 Goal 和进度推断当前步骤，超出了“只识别当前意图并选择工具”的角色。错误样本大量选中了同一 Goal 中的另一个真实工具，和该输入职责错位一致。

因此当前证据不支持 State Tuning。最小修复应先把 Selector 改为只接收 Strong Planner 已确定的当前 frontier/atom，并将它放在语义字节尾；Selector 不维护 Goal 语义 State，也不重新规划任务顺序。

## 冻结输入与产物

- G1J 2.9B vLLM 权重 SHA-256：`c1a316e75abd50f5edc3358fbb2c7d1cb18c611d9b2aa5b888091c8d45cc866c`
- 数据集：`rwkv_lh_network_selector_requirement_byte_tail_s60_v1`
- 数据集 SHA-256：`3b60bf7fd69a2d085480ffcac4b31eca0655e38a3a67bf2f308660f629ea3faf`
- 输入协议：`rwkv-lh.exact-tool-selector-input.v7-requirement-byte-tail`
- 初始 State：`zero`，SHA-256 为 64 个 `0`
- 特征清单 SHA-256：`01d808de23ad411776af2d2bf4251ef8e7c7e18d841bd7eee82a5be0228202f9`
- Head SHA-256：`e7897be5efbd4ef7e4d4ffb8d5158e4c542b277430e537fa30263b9e0fc77a3c`
- 开发集预测 SHA-256：`15b9fab5fe27603afc1e7e68e607bbf5c68d9174149f2d9dc2bd73a497594d39`
- 开发集结果 SHA-256：`04ceca0b33a521823ffb578b2e048046f14bcbe22dff4b65325b1b48befcaf50`
- locked test：未抽取特征、未打开、未评分。

## 固定 gate 结果

- S28 accuracy：`1.0`
- S39 accuracy：`0.9509918093681335`，要求 `>= 0.96`，失败
- S39 macro-F1：`0.9492750663784002`，要求 `>= 0.96`，失败
- S52 accuracy：`0.9749373197555542`
- S53 accuracy：`0.9846153855323792`
- S55 accuracy：`0.9958333373069763`
- 整体 eligibility：`false`

由于开发 gate 未通过，Head 不进入生产，也不允许打开 locked test。

## 最早失败记录

文件：`run_g1j_s60_h64_dev_selection_r2/DEV_PREDICTIONS.jsonl`

可直接回查的记录：

```json
{
  "dataset_id": "s39",
  "sample_id": "S60-10c5f52faf65e25fa6c4f124",
  "source_sample_id": "S56-86fc6108189e3e7edbb39ea7",
  "kind": "current",
  "language": "en",
  "position": 1,
  "label": "list_directory",
  "selected": "read_file",
  "raw_argmax": "read_file",
  "exact": false,
  "postprocessed": false,
  "label_corrected": false
}
```

该记录证明：协议已经完成解析并产生完整 logits；具体错误对象是工具分类字段 `selected`，不是格式字段。

## 全 S39 错误分布

- 总数：857
- 错误：42
- `kind=current`：19/500 错，accuracy `0.962`
- `kind=history`：23/357 错，accuracy `0.935574`
- 英文：32/429 错，accuracy `0.925408`
- 中文：10/428 错，accuracy `0.976636`
- position 0：20/500 错，accuracy `0.96`
- position 1：22/255 错，accuracy `0.913725`
- position 2：0/102 错，accuracy `1.0`

典型错误不是非法工具名，而是同一多步骤请求中的其他合法操作，例如：

- 目标 `move_file`，误选前一步 `write_json`；
- 目标 `write_json`，误选后一步 `move_file`；
- 目标 `final_answer`，误选已经完成的 `copy_file`；
- 目标 `read_json`，误选前一步 `read_file`。

错误 logits 的 top-1/top-2 margin 中位数为 `1.534154`，并非全部是接近边界的随机抖动；至少一部分是稳定地关注了错误步骤。

## 问题分类

1. 工程问题：Selector 输入仍把完整多步骤 Goal 放在语义尾，导致角色越界，已直接证实。
2. 模型/Head 质量问题：在该越界协议上 G1J 2.9B+h64 未达到预注册 gate；但在修复输入职责前，不能将差距归因于模型固有能力。
3. 格式问题：没有证据。失败记录的协议、logits、标签和输出字段均完整。
4. 基础设施问题：没有证据。特征抽取完成，State 为 zero，采样与文本生成均未启用。
5. 下游 13.3B：本轮是 Selector 离线开发集评估，尚未进入 Executor，因此不存在可归因给 13.3B 的下游错误。

## 最小修复与复测条件

只改一个地方时，修改 Selector 投影：将 Strong Planner 的当前 frontier objective 作为唯一任务语义并放在最后，去掉完整 Goal 重规划和 Selector 持久语义 State。保持同一 G1J 权重、同一 Head 架构、同一评价指标和同一阈值，重新抽取修复后协议的 train/dev 特征，再做固定 gate。

只有角色正确的协议仍在同类样本上稳定失败，且排除 Head/特征可分性问题后，才进入 State Tuning 数据构造。

## raw trace 需求

确认本轮最早失败层不需要打开更完整 raw trace；`DEV_PREDICTIONS.jsonl` 已含标签、原始 logits、argmax、最终选择和后处理标志。若要判断某一条线上 Goal 在 Selector 错误后，Executor 或 Audit 是否又产生独立错误，则需要对应线上 Goal 的完整 causal raw trace。
