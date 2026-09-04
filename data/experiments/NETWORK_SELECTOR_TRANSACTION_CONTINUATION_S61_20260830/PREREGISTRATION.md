# S61 当前轨迹 Selector 最小 state 消融预注册

- 冻结日期：2026-08-30（Asia/Shanghai）
- 实验编号：`NET-SEL-2P9-S61-TRANSACTION-CONTINUATION`
- 物理设备：仅 GPU0
- 目标：修复真实 Harness 中 2.9B Selector 在多根写入、观察后修改、失败恢复与结束边界上的错误，同时保留现有 25 类工具能力。
- 非目标：不修改 Planner/Executor 职责，不让 13.3B 重新选择工具，不动态屏蔽 `final_answer`，不修改、删除、隐藏、重排或修复任何 RWKV 原始输出。

## 已冻结的问题证据

1. S60 静态 locked test 已通过原有发布门，但 2026-08-30 三例真实 GPU0 canary 仍为 `strict=0/3`。
2. Harness 修复后，未覆盖全部写入根、没有成功 mutation 或 mutation 后过早结束均会 fail-close；因此旧的“假完成”不再计为完成。
3. 真实失败簇：
   - 完成第一个写入根后过早选择 `final_answer`；
   - 明确的写入/修改阶段误选 `list_directory`；
   - 观察文件后没有继续 `replace_text` / `patch_json`；
   - 多根写入只覆盖一个根；
   - 成功写入后未进入 `check_command`，或成功检查后未进入 `final_answer`。
4. S54 的 V4 语言模型标签 state 对固定 MLP head 的决策几乎无影响，不能作为“state 有效”的证据。

冻结输入：

| 输入 | SHA-256 |
|---|---|
| S60 cases | `3b60bf7fd69a2d085480ffcac4b31eca0655e38a3a67bf2f308660f629ea3faf` |
| S60 manifest | `16d05f9a7e4e5c94f3f314ec5848384b96b95045609fde25d92cfb3d497be76f` |
| V7 renderer | `312e490f92fcc0d20dc8a78038291d15e298e6c8e27ae20eaff41fe7f38686f0` |
| S60 locked-test result | `57e29bb78f1a75deacd23ad92f5c1689ed14e1e13aab7d6e9e8ad66efef6ae4c` |
| S54 state ablation result | `15295af545ab9bb12307a91ae9caf7d870629f90b7dbdba83cf7f63ccf2199d0` |
| bugfix canary result | `b6134fb68b0143562a953095f8ab676f53ae3236e10f9c7250ee117104a63bc5` |
| Agent Ladder tasks | `23cf009831fb38dd05bd3fad69e246a822a59ab6bd725833c6df2aaaf45c93bb` |
| Agent Ladder acceptance | `f95da0b4085cdee3bc4555255dfb4f09d9272c00982634c72a040361c5774e06` |

## S61 数据合同

数据集编号：`rwkv-lh.network-selector.transaction-continuation-s61.v1`。

固定规模：

| split | focus | S60 retention | 合计 |
|---|---:|---:|---:|
| train | 1000 | 1000 | 2000 |
| dev | 250 | 250 | 500 |
| test | 250 | 250 | 500 |

Retention 每类固定为 train 40、dev 10、test 10，并在每类内保持中英文各半。Focus 使用与生产一致的 V7 byte-tail 输入，覆盖以下边界：

1. 第一个文本或 JSON 写入；
2. 一个写入成功后继续第二/第三个写入根；
3. `list_directory` / `read_file` / `read_json` 成功后进入明确 mutation；
4. 检查失败后执行明确修复；
5. mutation 完成后执行 `check_command`；
6. 检查成功且全部义务完成后才 `final_answer`；
7. 过早结束被协议拒绝后仍选择剩余 writer；
8. writer 失败后重试同一职责；
9. `web_search` / `connector_lookup` 后落盘证据。

数据必须满足：

- train/dev/test 的实体、路径与 source-family 不交叉；
- 中英文在每个 split 的 focus 中各占一半；
- 只包含工具名称/描述、完整不可变请求、当前阶段和有界进度；
- 不包含参数 schema、工具结果正文、Executor 文本、Planner 文本或生成的 RWKV 文本；
- 当前问题位于续写末端，完整请求是最后语义字段；
- `prompt + target` token 边界可加，含 BOS 总长不超过 2496；
- 训练标签由预定义工作流当前位置机械产生，不使用 Ladder 答案或模型输出；
- Agent Ladder 仅作 holdout，不进入 train/dev，也不用于候选选择；
- 固定泄漏算法为 `utf8-byte-5gram-cosine.v1`，S61 请求对 Ladder 请求的最大相似度必须 `< 0.95`，并记录最大配对；
- Ladder 中出现的精确任务 ID、验收 marker 与工作区路径不得进入 S61。

test 在 dev 候选选定之前保持关闭，不提取特征、不计算指标。

## 固定模型与特征

- 基座：RWKV-7 G1I 2.9B，模型权重 SHA-256 `01f39dd59fc402fbe8ba49765a1997ee9dbc82427bf0ece6a4fac520e9eb8044`。
- 输入协议：`rwkv-lh.exact-tool-selector-input.v7-requirement-byte-tail`。
- 类别：冻结的 25 个工具名，顺序不变。
- 特征：同一次前向得到 current-step hidden mean 与 last，各 2560 维，拼接为 5120 维。
- Head：单隐层 h64 MLP；不做 logit 后处理。
- 任何特征提取和训练仅允许 `CUDA_VISIBLE_DEVICES=0`。
- 原始 hidden、25 个原始 logits 与 argmax 必须先存档；不得诱导、改写、裁剪或替换。

## 四臂消融

固定比较：

- A：S60 head + zero state（当前产品基线）。
- B：S61 head + zero state（判断数据/head 是否足够）。
- C：S60 head + S61 state（固定 head，测 state 的独立因果作用）。
- D：S61-state 条件下重训 h64 head + S61 state（测 state/head 联动）。

S61 state 使用且仅使用 2000 条 train，target-only loss，V7 标签后缀；步数 2000，保存 500/1000/1500/2000，seed 1061，父 state 为 zero。dev 不参与优化。候选按最早满足门槛的 checkpoint 选择。

若训练环境能在不改变 RWKV/vLLM 原始语义的前提下实现 MLP 分类损失直连 initial state，可作为预先编号的 E 臂单独运行；E 不替代 A-D，也不能在看到 test 后加入。若环境不支持，记录为未运行，不据此修改 A-D 的判断。

## Dev 选择指标与门槛

统一指标实现、类别顺序和 argmax，不允许结果后修改口径。

候选必须同时满足：

- S61 dev overall accuracy `>= 0.96`；
- S61 dev focus accuracy `>= 0.95`；
- continuation-vs-final boundary accuracy `>= 0.97`；
- focus 中每个有支持类别 recall `>= 0.90`；
- 对 A 的 focus net rescue `> 0` 且 changed decisions `>= 1`；
- S60 frozen dev 各既有 gate 继续通过；相对 S60 head 的任何冻结 source accuracy 回归不得超过 1 个百分点；
- generated RWKV text 数量为 0，logit postprocessing 数量为 0，raw logits 未修改。

Head/state 最小化规则：

- B 达门且 D 相对 B 的 focus accuracy 增益 `< 0.02`，并且真实 canary 没有额外闭环增益：发布 B，保持 zero state。
- D 只有在相对 B 的 focus accuracy 增益 `>= 0.02`，或在保留门全过时让冻结真实 canary 增加至少一个 strict/transaction-complete case，才可启用 state。
- C 若退化，不得通过换 head 掩盖其“固定 head 无独立增益”的事实；报告必须保留 C。
- 多个 state checkpoint 合格时选择最早 checkpoint；不在一次 run 中切换 state。

## Locked test、真实闭环与 13.3B 后续

Dev 选定唯一架构后才打开 S61 test。Test 门与 dev 相同，且不允许重新选 checkpoint/hyperparameter。

随后按顺序运行：

1. 原 S60/S28/S39/S52/S53/S55 全量 locked 回归；
2. 2026-08-30 三例 bugfix canary 原样重跑；
3. 十例 Agent Capability Ladder 原样重跑；
4. 联网检索质量固定集原样回归；
5. 全项目测试、边界/异常与 raw-output 完整性检查。

只有 Selector 正确选中工具后，才按真实残差判断 13.3B Executor：

- 选对工具但参数/内容/修复/总结错误，归入 13.3B state-tuning 数据；
- Selector 仍选错，不得用 13.3B 补偿；
- 13.3B 的 G3（offline）与 G6（network）状态继续分开保存，run 内不切换；
- 是否增加新的 13.3B state 由固定残差簇和最小状态原则决定。

## 完成条件

实验报告必须给出数据哈希、代码哈希、GPU0 证明、四臂逐项指标、混淆矩阵、changed/rescued/regressed 样本 ID、locked test、真实 canary、Ladder、联网质量、服务身份与产品 18070 未受影响的证据。若门槛未达到，结果必须如实记为拒绝，不能通过控制器特判或输出干预伪造成通过。
