# EXE-G6：联网任务级 Executor state 与协议拒绝恢复预登记

登记时间：2026-08-29（G6 数据生成、训练和 V2 holdout 首次运行之前）。

## 已观察根因和架构边界

S60 选择器、G3/G4/G5 执行态以及真实联网 V1 的固定结果表明，检索后端不是当前阻塞项。G4 与 G5 在 URL→文件任务上均先生成包含正确证据的 `write_file`，但把目标写成绝对路径；Harness 按既有安全契约拒绝后，13.3B Executor 没有只修正路径，反而重复绝对路径或把 `content` 退化成 `content_refs`。G4 训练集 train2,000/dev480 中 `protocol_rejection` 输入均为 0，根因是通用拒绝恢复分布缺失，不是单个 URL 或文件名。

G6 不替换通用 G3，也不在一个 run 的阶段之间切 state。运行策略固定为：离线/通用任务继续使用 G3；显式不可变 `retrieval.mode != offline` 的任务在 Executor lane 创建时加载一个 G6 网络 profile，并在该 run 全程保持，`profile_switches_within_run=0`。选择依据来自已有 runtime policy，不做关键词路由。Selector 仍是独立 2.9B S60 hidden mean+last→h64 MLP raw-logit argmax；G6 仅属于 13.3B Executor。

G4 step2000 是 G6 parent：它在 G4 dev480 上为 447/480 canonical exact，且 `write_file` 34/40、`write_json` 28/40、`web_search` 15/16、`connector_lookup` 16/16，显著强于已拒绝的 G5 网络候选。G4 作为 G6 的训练 parent 不改变其未获准做全局 profile 的事实。

## 冻结输入身份

- 13.3B base model SHA-256：`5d97772ba04a81bdaeba90e1d6d306c70560bf4f784522be61cdcade69e30562`。
- parent training state：G4 step2000 `rwkv-step-2000.pth`，SHA-256 `85f06763e776513acca86d5f8b23ea46bfe985a23b4d151c73ede01f833bdaaa`。
- parent vLLM state SHA-256：`c4e9e8ae01e829aa1c369945fa46ae287d900b3fa98dd06ae54ab2ef5d6ef946`。
- G4 train/dev source SHA-256：`f5a1e2d3a06c487f589001ae988fe4fe7a6a4540e8ca0b5121a8af40890e93` / `a81f3805535649ae75148e0d7debdb3be60e00ba36837b67d0f80fb8113bb50d`；manifest `ad0781511f2ebc57b30a44dc7cb82daccf43f9871de7d36bcdbd58aeae9c831f`。
- V1 holdout cases SHA-256：`971c89f2def921498b664e069f4af281857aac377bec881ce04d2c57fbb66708`。
- 在训练前冻结的 V2 holdout cases SHA-256：`d8ad5bd999d26b6b16292fae7503534dcb01d3f8ae0c7a1d9c78c93d1d1deb31`；manifest SHA-256：`77572aca4d6afcfc0ba4d2c217c93d32f2b2f7476fa506fbbc44060c8dd604f4`。

## 固定 G6 数据

总量保持约 2,000。所有 target 均由程序按当前 Harness contract 构造，不使用任何 RWKV 生成文本。

Train 2,000：

- 800 条冻结 G4 true-workflow retention（原 800 条全部保留）；
- 400 条冻结 G4 direct retention（24 个 operation 各 16 条，再给 `write_file` 与 `write_json` 各 8 条）；
- 400 条新的 clean network-stage：`web_search`40、`connector_lookup`40、`write_file`100、`write_json`100、`read_file`30、`read_json`30、`bind_evidence`20、`file_digest`20、`final_answer`20；
- 400 条新的 protocol-rejection recovery：`write_file`120、`write_json`100、`read_file`30、`read_json`30、`append_file`20、`copy_file`20、`move_file`20、`file_digest`20、`web_search`10、`connector_lookup`10、`bind_evidence`10、`final_answer`10。

Dev 480：

- 240 条冻结 G4 true-workflow retention；
- 96 条冻结 G4 direct retention（24 个 operation 各 4 条）；
- 72 条 clean network-stage：8、8、16、16、6、6、4、4、4，operation 顺序同上；
- 72 条 protocol-rejection recovery：`write_file`20、`write_json`16、`read_file`6、`read_json`6、`append_file`4、`copy_file`4、`move_file`4、`file_digest`4、`web_search`2、`connector_lookup`2、`bind_evidence`2、`final_answer`2。

新数据的 train/dev entity、路径、查询和语言模板 family 必须不相交。拒绝输入使用生产 `ModelEvent(event_type="protocol_rejection")` 与 `render_event_append(..., independent_executor_retry_operation=...)` 原样渲染；原始不可变任务保留在已披露 contract 中，最后一个 closed field 是 `current_question`。clean 输入最后一个 closed field 是逐字 `current_requirement`。绝对路径只作为明确标记 `action_executed=false` 的 rejected arguments 出现，正确 target 始终保持 workspace-relative；不得放宽 Harness、推断参数或重写模型输出。

对所有新 train/dev 请求与 V1+V2 的 8 个 holdout 请求使用 byte 5-gram cosine；最大值必须 `<0.75`。固定 ctx2496，任何 target 不得截断；exact prompt duplicate 和 train/dev source-family overlap 均为 0。

## 固定训练

- server physical GPU0，且 UUID 必须仍为 `GPU-1faf7f09-25f4-2515-b707-6e0766aa841d`；现有产品端口 18070 全程受保护；
- parent 为上面的 G4 training state，只加载一次，不与 G3/G4 state 叠加；
- PEFT state、FLA、BF16、target-suffix loss、JSONL BOS 0、ctx2496、batch1、gradient checkpointing；
- seed1067；2,000 steps；每 250 steps 保存；LR `2e-6 -> 2e-7` cosine；warmup40；Adam beta1 0.9、beta2 0.99、eps1e-8。

## 固定 checkpoint 评测和选择

必须先验证 step250/500/750/1000/1250/1500/1750/2000 的 state tensor、parent、base model、GPU0 和 vLLM 转换身份。随后用同一 temperature0.1、top-p1、top-k0、单次 raw-first 评测 parent G4 与全部八个 checkpoint，数据固定为冻结 G4 dev480 和 G6 dev480。按步数从小到大选择第一个同时满足：

1. 两个 dev 的 transport、response envelope、schema 和 selected operation 均为 100%；
2. 冻结 G4 dev canonical exact 不低于 parent 的 447/480，且 `write_file>=34/40`、`write_json>=28/40`、`web_search>=15/16`、`connector_lookup=16/16`；
3. G6 dev canonical exact `>=456/480`；其中 clean `>=68/72`、protocol-rejection recovery `>=65/72`、336 条 retention `>=323/336`；
4. recovery 的 12 个 operation 均 schema-valid、operation-correct，且每个 operation canonical recall `>=0.80`；
5. 相对 parent G4，G6 recovery 有正 rescue、净提升为正；
6. state attestation、request/question-at-tail、append-only raw journal 和 first raw output 完整；hidden retry=0、postprocessed=false、原始 RWKV token/output 未修改、未删除、未重排、未隐藏。

未通过的 checkpoint 不得激活，也不得在看到结果后放宽指标。

## 发布门

Dev 候选确定后才可首次打开 V2。最终网络 profile 必须同时通过：V2 6/6、历史 V1 2/2、检索质量固定 9/9 hard gates、相关单元/集成回归和 Full90 dispatch/integrity。若失败，G3 生产默认和现有联网 V1 保持不变；不得以 controller 特判、路径自动修复或修改 RWKV 输出代替 state tuning。
