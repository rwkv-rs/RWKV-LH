# S60：完整要求位于 Selector 字节尾部的预登记

登记时间：2026-08-29（任何 S60 数据生成、特征提取或 Head 训练之前）。

## 已观察根因

S59 的冻结分类测试满足全部门槛，但在固定真实 Harness 中只有 4/6。M03 在成功 `read_json` 后应选择“创建或替换完整 JSON 值”的 `write_json`，S59 raw argmax 却选择了“保留所有未指定顶层键”的 `patch_json`，最终保留旧 `users`、`active`、`fullname` 与 `legacy_note`，并把数值 schema 写成字符串。该结果不是 13.3B 参数错误，而是 2.9B operation 边界错误。

S59 V6 的最后字节是固定通用问句，完整要求位于该问句之前。对于“删除旧字段”与“保留未指定字段”这类互斥语义，固定问句会把真正决定 `write_json`/`patch_json` 的要求推离续写点。这与用户已确认的经验不完全一致：实际要求或问题本身应位于输入末端。

## V7 固定输入

S60 使用新协议 `rwkv-lh.exact-tool-selector-input.v7-requirement-byte-tail`。bootstrap 仍只包含 25 个工具的名称、描述、menu identity 与 task SHA；每个 step 依次包含 schema、bounded progress、stage role，最后一个顶层字段仍为 `current_question`。其内部固定顺序改为：

1. 通用选择问题；
2. 当前阶段；
3. 完整 immutable requirement，且它是紧邻续写点的最后字段与最后语义字节。

Selector 仍看不到参数 schema、Executor 文本或完整工具结果。该布局是全局协议修正，不包含 M03、`users.json`、H10 或 verifier 的专用字符串与规则。

## 数据、Head 与门槛

逐行重渲染冻结 S58 数据；标签、split、source、轨迹、可辨识修正和数量不变：train 13,143、dev 2,571、test 2,579。只改变 V7 bootstrap、prior steps、current step 与 rendered input。prompt 必须唯一，完整要求在每个 step 恰好一次并位于该 step 的 JSON 字节尾部。

Head 配置保持：2.9B zero state、same-forward Hidden concat(mean,last)、fresh Xavier h64、seed 1059、dropout 0.05、AdamW lr0.001、weight decay0.0001、batch128、cosine、最多160 epoch、patience30、gradient norm1.0、每个 `(source,label)` 相同总权重。dev 选择前不解析 test。

门槛不变：S28 accuracy/macro-F1 >=0.99；S39/S52 accuracy/macro-F1 >=0.96；S53 accuracy/supported-macro-F1 >=0.96；S55 accuracy/supported-macro-F1 >=0.98 且每个支持类 recall >=0.90；portable raw-logit replay argmax 相同、最大绝对差 <=0.005。通过 dev 后只打开一次固定 test，并要求同一门槛。

通过离线门槛后，S60 必须与 G3/G5 在相同 6-case 真实 Harness 中重新运行。任何失败都不得通过阈值覆盖、logit 后处理、重选、规则特判或修改 RWKV 原始输出修复。
