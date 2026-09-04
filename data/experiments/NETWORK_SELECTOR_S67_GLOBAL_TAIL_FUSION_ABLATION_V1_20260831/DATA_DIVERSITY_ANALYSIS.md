# S67 Global + Tail 融合后的数据多样性分析

日期：2026-08-31（Asia/Shanghai）

## 固定结果

- 融合结果：`run_global_tail_fusion/ABLATION_RESULT.json`，SHA256 `aa94aa036254f8b7e7953b715d4f924ecdd5b44c0a40cb10f653aa5ada73c678`。
- `zero`：accuracy `0.932`、macro-F1 `0.9287127643394296`、最低 recall `0.50`。
- `ST1500`：accuracy `0.924`、macro-F1 `0.9195025347072623`、最低 recall `0.45`。
- 两个候选都未达到预注册的 `0.96 / 0.96 / 0.90`，因此未选择候选；state tuning 在此目标上没有收益。

## 完整数据影响范围

`zero` 的 500 条 dev 中，低于 `0.90` recall 的类别只有：

| label | recall | 主要去向 |
|---|---:|---|
| `append_file` | 0.50 | `remove_line`、`write_file`、`write_json` |
| `copy_file` | 0.65 | `move_file` |
| `replace_text` | 0.55 | `write_file`、`remove_line`、`bind_evidence` |
| `write_file` | 0.75 | `append_file` |

`move_file` 本身不是低 recall 类，但它是 `copy_file` 的主要吸收类，所以同属必须 contrastive 覆盖的语义边界。英文 dev accuracy 为 `0.952`，中文为 `0.912`；五个边界类在中文上更弱。

## 根因证据

S67 generator 的 `request_for` 通过 `split_index` 为每个 label、每种语言、每个 split 固定选择一条操作核心句式。train 的 80 条/label 实际只有：

- 英文一条操作核心句式 + 3 个通用 modifier；
- 中文一条操作核心句式 + 3 个通用 modifier；
- 其余变化主要来自路径、随机标识和词根。

dev 会把同一 label 换成另一条此前从未用于 train 的核心句式。因而当前 2K 数据在计数上平衡，却没有 2K 条相应的语义覆盖；它更容易学习路径/批次变化，不能充分学习同义操作边界。融合 head 的 train 指标达到 `1.0` 而 dev 停在 `0.932`，与该数据根因一致。

## 整改边界

下一数据版本只修复全数据统计支持的五类 contrastive 边界：

`append_file / write_file / replace_text / copy_file / move_file`。

保持不变：25 类、CurrentDirectStageV2、V7 byte-tail、2,000 train / 500 dev / 500 locked test、跨 split 词根隔离、Ladder/E3 隔离、RWKV 2.9B、Selector/Executor 职责边界、评价指标和门限。训练集必须为每个边界 label/语言提供多条操作核心句式；dev/test 使用未见核心句式。该整改不得加入关键词规则、标签特判或 logits 修正。
