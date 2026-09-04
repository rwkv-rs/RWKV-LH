# RWKV-LH 三阶段残差 State Tuning v1 预注册

日期：2026-08-26（Asia/Shanghai）

## 总原则

三阶段都只训练已经在真实 Harness 运行中发现的错误状态迁移，不把通用任务完成、强模型
transport failure、Controller 工程缺陷或 benchmark reference answer 转成 state 标签。每一阶段
必须先冻结数据、评价集、参数和通过门，再训练；下一阶段的数据只能由上一阶段的固定评价残差
决定。

所有阶段从上一阶段选定 state checkpoint 连续初始化。不得把后续阶段重新从 zero state 开始，
也不得根据 dev 结果从多个 checkpoint 中事后挑最好者。checkpoint 只按预注册 final step 选择，
除非出现 non-finite、文件不完整或训练进程失败。

## Stage 1：selector 外层协议身份

### 观测根因

Round1 frozen dev200 中有 79 个 selector boundary：77 个输出直接 concrete tool，只有 2 个合法
`select_tool`，且这 2 个仍选择错 inner operation。错误 concrete outer functions 为：

- `list_directory`: 41；
- `read_file`: 18；
- `read_json`: 15；
- `connector_lookup`: 3。

相同运行的 direct boundary 为 121 条，118 条 operation 正确。因此 Stage 1 不再混合 direct
参数学习；只强化“当前 boundary 必须先调用 select_tool”这一状态身份。

### 冻结数据

- 来源：Round1 已通过 Controller replay、holdout contamination 和远端 tokenizer 验收的
  selector rows；不合成新任务答案。
- train：500 条、100 个完整 semantic families，每个 family 5 个 surface variants。
- dev：Round1 全部 79 条 selector dev rows，零训练重叠。
- 每个 target 的 outer function 必须严格为 `select_tool`；inner name 仍由原 private oracle 决定。
- hard-negative registry 只记录上述四类真实 concrete outer functions，不作为正 SFT 文本。
- loss mask：`target_suffix`；历史 Assistant span 的 supervised token 必须为 0。

### 冻结训练参数

- parent state：Round1 step 2000，SHA-256
  `601c3c4df8c6e82918efa36d5425626eb9cffa4a0c5f0512da83aa5063e423f5`；
- GPU0、`--peft state --op fla`、bf16、ctx 2496、micro batch 1；
- 500 steps、1 epoch、shuffle、seed 827；
- LR `5e-5 -> 1e-5` cosine、warmup 20；
- step save 100；选择 final step 500。

### 固定评价与门

使用 native sampler，temperature 0、seed 826、相同 79 selector dev，分别评估 parent 与 Stage 1
child。主指标为严格 `parse_tool_selection` schema-valid，次指标为 inner operation accuracy。
同时在原 dev200 的 121 direct rows 上检查回归。

Stage 1 通过必须同时满足：

1. parent/child 服务都通过 state SHA、源码树、adapter 和 request-row attestation；
2. selector schema-valid 相比 parent 至少净增 8/79，且绝对率至少 10%；
3. selector inner-operation 至少净增 4/79；
4. direct operation accuracy 相比 parent 下降不超过 2/121；
5. child -> parent -> child 的两个 child 结果逐项一致；
6. state 文件 61 tensor、bf16、finite、nonzero。

若未通过，不把该 child 作为 Stage 2 parent；Stage 2 必须使用 parent state，并把失败归因到
schedule/state capacity 或 stage target strength，不能用工程规则隐藏。

## Stage 2：completion 与 no-progress 残差

Stage 2 的精确数据量、类别比例和 schedule 只能在 Stage 1 固定评价完成后追加预注册。入口候选
仅包括：已有正确外部结果后的 `final_answer`、重复低信息 action 的抑制、错误参数合同后的同工具
纠正。selector 已通过的行不再重复加入。

## Stage 3：Stage 2 后的剩余缺陷

Stage 3 同样在 Stage 2 固定评价后追加预注册，只训练仍可归因于 RWKV state transition 的残差。
最终必须运行 selector/dev200、ECRA route120、RWKV-only E2E90、强 supervisor 可用部分、全部工程
回归，并把 supervisor transport availability 与模型行为分开报告。

## 评价口径冻结

- selector/direct：exact parser、operation、arguments，不以语义主观判断替代；
- paired comparison：相同 row ID、prompt SHA、sampling、max tokens；
- route/E2E：沿用现有冻结 verifier 和 similarity version；
- strong API 非重试 4xx 记 transport unavailable，不记成 RWKV state failure；
- 任一数据或代码路径发现新问题后，扩展检查全部同类行及相关代码路径。
