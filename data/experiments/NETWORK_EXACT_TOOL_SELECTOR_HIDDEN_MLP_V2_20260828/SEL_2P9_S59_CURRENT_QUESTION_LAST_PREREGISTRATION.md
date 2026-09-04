# S59：完整任务与当前决策问题共同末置预登记

登记时间：2026-08-29（Asia/Shanghai），发生在 S59 数据生成、特征提取与
Head 训练之前。

## S58 结果与协议根因

S58 V5 locked test 的各来源总体 accuracy 均达到门槛：S28 0.997333、S39
0.964994、S52 0.980344、S53 1.0、S55 0.983333；但 S55 `write_json`
recall 仅 26/30=0.866667，未达到已冻结的 0.90 逐类门槛，故 S58 不发布。
冻结结果 SHA-256：
`b88b5f199f593c89ae6d3828d57b60a5e19c269fbb0e52468aa191b0b6fe7ff9`。

4 个错误全部来自 `failed_check_dual_output_recovery` position 2：已经成功
`read_file` 与 `read_json`，应进入 `write_json`，但预测回到 `read_file`。
V5 虽把完整 immutable task 放在最后，却把描述“刚完成什么、现在选择什么”的
current stage 放在更早位置；长任务文本重新占据 continuation edge。这不完全满足
全局输入原则：“稳定背景/状态/证据在前，当前完整问题在最后、紧贴续写点”。

## V6 固定输入

S59 使用 `rwkv-lh.exact-tool-selector-input.v6-current-question-last`：

- bootstrap 仍只有 25 个 tool 的 name/description、menu identity 和 task SHA；
- step 依次为 schema、bounded progress、stage role，最后一个顶层字段为
  `current_question`；
- `current_question` 内依次为 `complete_requirement`、`current_stage`，最后为
  固定问题 `Select exactly one described tool for the next operation now.`；
- 因此完整任务、当前阶段与真正要回答的问题共同位于 continuation edge，同时
  Selector 仍看不到参数 schema、Executor 输出或完整工具结果。

冻结 V6 renderer SHA-256：
`a54ee775e3cea4c4614911ca042a804a7c2f896ccba7fc9d2ed40255cc45f4c4`。

## 数据、训练与隔离

S59 从冻结 S58 cases
`d49f938eb67858f3f17cf7e47672f5ec1b1d01918bd6e0b48e3dd1212399ebf0`
逐行重渲染。标签、S58 可辨识修正、split、source、轨迹位置、语义和样本数量
完全不变；只改变 bootstrap/step/prior-step/rendered-input 的协议字节。预期仍为
train 13,143、dev 2,571、test 2,579，25 类在各 split 的覆盖不变，prompt 无重复。

S59 仍只训练一个最小 Head：fresh Xavier h64、zero selector state、same-forward
Hidden concat(mean,last)、seed 1059、dropout 0.05、AdamW lr0.001、weight decay
0.0001、batch 128、cosine、最多 160 epoch、patience 30、gradient norm 1.0，
每个 `(source,label)` 支持组合具有相同总权重。只读取 train/dev；test 在 dev
选择完成前按原始行的 split marker 跳过且不解析。

dev 门槛保持不变：S28 accuracy/macro-F1 >=0.99；S39/S52
accuracy/macro-F1 >=0.96；S53 accuracy/supported-macro-F1 >=0.96；S55
accuracy/supported-macro-F1 >=0.98 且每个支持类 recall >=0.90；portable raw-logit
replay argmax 相同、最大绝对差 <=0.005。

S58 test 已经打开，S59 不再把它用于任何候选、epoch、参数或阈值选择；只在 S59
dev 通过后将同一批固定任务按 V6 重渲染为历史回归集并运行一次。之后必须继续过
真实 Harness factorial 6/6、live-network 2/2、retrieval-quality 9/9 与 Full90。
任何 downstream 失败都不通过修改阈值、logit、raw argmax 或 RWKV 原始输出解决。
