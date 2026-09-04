# RWKV Action State Tuning v1 预注册

日期：2026-08-26（Asia/Shanghai）

## 目标与边界

本轮生成第一次可训练的 RWKV-LH Action State Tuning 数据。沿用
`/home/chase/GitHub/RWKV-state-factory` 的私有 oracle、冻结环境回放、只接收
verifier 通过正样本、污染/多样性闸门和可审计导出方法，但不复用其 Web Retrieval
任务 schema、verifier、renderer 或污染算法。

训练目标限定为 RWKV action lane：operation 选择、progressive contract 披露后的完整参数、
真实 Observation 状态传递、Network Gate typed rejection、协议纠错和完成决策。Strong Planner
的合同图 JSON、评测答案和 Harness 语义路由都不进入 target。

## 冻结来源

- `seed_templates.jsonl` SHA-256：
  `33038741ba6b00373bfd84ca596df661865ebe79e2ed9016a65b72d2b7620bdb`
- `SYNTHESIS_PROMPT.md` SHA-256：
  `3cfe8809e85862c3b3505e54f5f45dbb4e4bbcbe466c3d4a166e562484935a84`
- `tool_contracts.json` SHA-256：
  `1afba2a1cbbb5faedd1098d165944ff23aa7574726a57a24a923a0d73c7957f8`
- Web factory `DESIGN.zh-CN.md` SHA-256：
  `9f228a0fec87d43738aded84bf003b1e8c2e740b2326f458863df094ddb7d229`
- Web/action 边界文档 SHA-256：
  `3fd7f415cb3898aeb591dfa0b3b6c3bca2361210d0ab34538753694165c1bbee`

冻结 holdout 为 ECRA route120 与 canonical RWKV-E2E-90，共 210 条 request：

- `data/datasets/rwkv_lh_ecra_route_v1/cases.json`
- `benchmarks/rwkv_e2e/rwkv_e2e_30/tasks.json`
- `benchmarks/rwkv_e2e/rwkv_e2e_extension48/tasks.json`
- `benchmarks/rwkv_e2e/rwkv_e2e_lh12/tasks.json`

不得读取 reference answer、hidden acceptance 或历史 benchmark trace 来生成候选。

## 固定规模与切分

- 20 个 seed，每个 seed 6 个预先定义的 semantic entity family。
- 每个 semantic family 4 个 surface/argument variant。
- 总计 480 条 verified trajectory。
- 每个 seed 的第 6 个 semantic family 固定为 dev，其余 5 个为 train。
- 预期 trajectory 切分：400 train / 80 dev。
- 同一 semantic family 不得跨 train/dev。
- 中英文在每个 semantic family 内各 2 条。

本轮属于 State Factory Phase A（300--600 高质量 bootstrap）。它不宣称达到完整建议量
1824 条；后续递归扩展必须继续使用同一 verifier 和污染口径。

## 生成方式

1. 由固定、可复核的私有 oracle 机械实例化 request、workspace fixture、参数和预期局部事务。
2. 合成器不生成 Controller event、工具输出、receipt、evidence ID 或验证结论。
3. 使用当前 `LongHorizonController`、`LongHorizonModel`、progressive G1i renderer 和
   `ActionHarness` 在一次性 workspace 中回放。
4. 网络成功样本只使用冻结 `.invalid` evidence；禁止真实联网。隐私样本使用
   `SYNTH_SECRET_DO_NOT_EGRESS_` 前缀，且验证 backend execution count 为 0。
5. 每个普通 target action 导出 selector 与 direct-call 两个监督 stage；协议拒绝纠错样本只导出
   保留已披露合同后的正确 direct call。故意 malformed 的输出不进入正向 SFT。
6. Prompt 字节必须来自本次实际 ModelSession 请求；不得由合成器仿写。

这里采用 State Factory bootstrap 的确定性 oracle 方式，不让强模型充当动作真值生成器。强模型
只能在后续递归扩展中产生候选表面或作为独立 reviewer；其输出仍须通过相同回放和 verifier。

## 固定验收

单条 trajectory 仅在全部成立时接收：

- request、workspace path、operation、完整 params 与 seed oracle 一致；
- selector/direct-call 均能通过当前 parser 和 authoritative tool contract；
- 本地 action 在 Harness 中实际执行，Observation 来自真实结果；
- Observation literal binding 精确成立；
- mutation 有 inspection 和 fresh read-back；
- Gate rejection 保留原参数、不重写、不重试，且 backend execution count 为 0；
- provider unavailable 后不重复相同 retrieval，final 不声称未观察事实；
- protocol rejection 后复用已披露 operation contract，malformed attempt 不执行 action；
- final_answer 只在 seed 明确要求时进入正向监督；
- run 可以在冻结脚本下正常终止，所有正向 target 均与实际 generation prompt 一一对应。

允许最多 2 次候选修复，但不得修改冻结 verifier、阈值或 holdout。确定性实例化失败视为生成器缺陷，
修复根因后重跑全部同类场景。

## 固定数据闸门

- trajectory 数：恰好 480；train/dev：恰好 400/80。
- seed 覆盖：每个 24；semantic family：每个 4。
- SFT 正样本解析通过率：100%。
- verifier 接受率：100%，否则不导出训练包。
- 内部 exact request duplicate：0。
- 内部 UTF-8 byte 5-gram cosine 最大值：记录但不以同一 semantic family 的四个表面变体为污染；
  跨 semantic family 必须 `< 0.75`。
- 对 210 条 holdout 的最大 UTF-8 byte 5-gram cosine：严格 `< 0.75`。
- exact holdout overlap：0。
- dev semantic family 与 train 交集：0。
- 正样本中的真实秘密、真实 credential 格式、holdout ID：0。

## 固定导出

- public semantic candidates；
- private oracle trajectories；
- per-trajectory validation report 与 rejected attempts；
- stage-level SFT train/dev；
- RWKV 官方 `{"text":"..."}` train/dev JSONL；
- manifest、文件 SHA-256、计数、污染/多样性指标和生成说明；
- 实验 `RESULT.md`。

