# EXE-G8：联网与旧工程能力联动修复预登记

登记时间：2026-08-29（G8 数据生成、训练、checkpoint 推理及 live 运行之前）。

## 目的、结论边界与 state 架构

G6 step1500 已把冻结网络面从 G4 parent 的拒绝恢复 `55/72` 提升到 `72/72`，clean network-stage 也为 `72/72`，但旧 workflow retention 只有 `310/336`。G7 从该 G6 state 继续训练，使用 1,040/1,200 条 retention replay；完整八 checkpoint 消融后，网络面在每个 checkpoint 都保持 `144/144`，但 retention 只有 `305/336` 到 `310/336`，没有候选通过。

G7 后验分析已冻结：单一 profile 最好 `310/336`；按任务族在 G6 与八个 G7 state 中固定选择也只有 `314/336`；即使不符合当前架构、按 operation 切 state 也只有 `314/336`，family+operation 为 `315/336`；逐条事后挑最佳的不可部署 oracle 也只有 `316/336`。因此不能通过增加 state 路由、阶段切换或多次模型调用达到 `323/336`，必须训练新 state。

20 条用例在 G6 parent 和全部 G7 checkpoint 中持续失败：discount ledger 与 failed-check recovery 占 19 条，集中于错误检查后精确重建 JSON 的结构/数值、长轨迹路径与文本保持、最终完成语句；另有一条 direct web query 冠词保持。G7 已证伪“只提高旧 workflow 总占比即可修复”的假设。G8 修复的是训练多样性与关键位置监督密度不足，不再复用同一批 20 条 trajectory 做低学习率 replay。

G8 仍是 13.3B Executor 的**任务级** network+workflow profile：一次 run 只绑定一个 state，`profile_switches_within_run=0`；不得叠加 state，不按当前 operation 临时切 state。2.9B S60 Selector 仍只看工具描述并选择 tool，G8 不承担选择职责。只有离线、live 与引擎切换全部通过后，才允许与 general profile 组成最小双 state 正式版本。

## 冻结证据与身份

- G7 ablation SHA-256：`18f00ac2bcd5bb18983ad5e569ae173141a65f68b7bbf2e4c186fc7414900133`；状态 `no_candidate_passed`。
- G7 failure analysis SHA-256：`474094c81175377dcfceb243af667b6278755f365adf9a5426a978c1d8451a3d`。
- G4 deterministic workflow generator SHA-256：`c15f3947069ea1fd01efa7cf772b479cf53a8e2b6289424355a9cc6f3dbf89a6`。
- 13.3B base SHA-256：`5d97772ba04a81bdaeba90e1d6d306c70560bf4f784522be61cdcade69e30562`。
- parent training state：G6 step1500，SHA-256 `648dcdc665ddae69f519718d9b1b6033d354255bfbeeaf9eed6d6a07088c1b78`。
- parent vLLM state：G6 step1500，SHA-256 `611d9e5564ef47413c1bd1536500e987270c8303b2c87d5d54bca256d57dd68b`。
- G4 train / manifest：`f5a1e2d3a06c4877bf589001ae988fe4fe7a6a4540e8ca0b5121a8af40890e93` / `ad0781511f2ebc57b30a44dc7cb82daccf43f9871de7d36bcdbd58aeae9c831f`。
- G6 train / manifest：`ea3f62b22a6269e8b7d43b71386909532945085ff206d5fa0d530c4fc37519e6` / `b5f960a51a418d45b246bf454a3df8b9c326c0ded66af0e05cb05700a04f3c17`。
- 冻结 G4 eval / manifest：`f89ff7828dfa298eedfab6c2cef531708fac7e812e9c309530086a5192770e5d` / `d8dad84b355df504a5162017fedf3fd97036f91485869314187a513b6e71d5cf`。
- 冻结 G6 eval / manifest：`f80f7452f5dcc38b8932de50eb391e6b8cbd0f494cbab40b4b8d4b8db6d072ee` / `ba3bb05085c9055b3230fdb79ed859146ddf46d586c8d0f0f3c30b40c810eb3e`。
- live V1/V2：`971c89f2def921498b664e069f4af281857aac377bec881ce04d2c57fbb66708` / `d8ad5bd999d26b6b16292fae7503534dcb01d3f8ae0c7a1d9c78c93d1d1deb31`。

失败分析只能决定 family、operation 与 trajectory-position 的总体配比。不得把 G4/G6 dev、G8 holdout、live V1/V2 的 sample ID、请求、target 或 RWKV 输出复制到训练集；不得对 20 个失败 ID 做字面特判。

## 固定 G8 train2000

所有新 workflow prompt/target 由上面冻结的 G4 确定性生成器产生，不包含采样 RWKV 文本。训练总计 2,000 条：

1. `1,200` 条新 targeted full workflow：
   - discount ledger：`train` index 20–94，共 75 个完整八步 trajectory、600 条；
   - failed-check recovery：`train` index 20–94，共 75 个完整八步 trajectory、600 条。
2. `240` 条新 broad full workflow：implementation/public-evidence/connector-record 各 `train` index 20–29，10 个完整八步 trajectory、每族 80 条。
3. `240` 条 G4 direct replay：24 个 operation 按训练 sample ID 各取前 10 条。
4. `160` 条 G6 network replay：clean 80、protocol-rejection recovery 80，operation 配比与 G7 完全相同。
5. `160` 条新 critical-position supervision，不复制 dev 文本：
   - recovery write_json 60（index95–154）；discount write_json 30（95–124）；
   - discount write_file 20（125–144）；discount final_answer 15（145–159）；
   - recovery final_answer 15（155–169）；discount verifier read_file 10（160–169）；
   - discount read_json 5（170–174）；G4 train 中 direct web_search 的第 11–15 条 5。

因此新生成的完整 workflow 为 1,440/2,000，关键失败族完整轨迹为 1,200/2,000；另有 160 条仅提高关键位置监督密度。critical-position 行只用于增加 target-suffix 监督，不会作为 controller 特判，也不改变运行时输入。

数据硬约束：

1. exact prompt duplicate=0；sample ID、prompt SHA 和 source family 均唯一可追踪；
2. 所有 `text == prompt + target`，target suffix 与当前 Harness contract 100% 合法；
3. literal `current_requirement` 必须为 continuation JSON 最后字段并紧邻续写点；ctx2496 下 target truncation=0；
4. train 与 G4/G6 dev、G8 holdout 的 source identity overlap=0；
5. 对 live V1+V2 请求使用固定 byte-5-gram cosine，最大相似度 `<0.75`；
6. `generated_rwkv_text=false`、`raw_output_modified=false`；绝不修改、删除、重排、诱导或隐藏 RWKV 原始输出。

## 新的冻结 G8 holdout240

在训练和任何 G8 推理前，用冻结 G4 生成器重建未进入 13.3B Executor train/dev 的 `test` split index0–5：五个 family 各 6 个完整八步 trajectory，共 240 条。holdout 只写入 `data/datasets/` 并记录 generator/source/hash；永不进入 G8 train。

这组 holdout 用于验证 G8 不是只适配已反复使用的 G4/G6 dev。其 family、operation、参数 schema 与真实 harness 相同，但 token、路径、值、请求表达和 source identity 与训练分离。

## 固定训练

- 只使用 server physical GPU0，UUID `GPU-1faf7f09-25f4-2515-b707-6e0766aa841d`；18070 产品服务全程保护；
- 从 G6 step1500 training state 精确初始化一次；不从任何 G7 checkpoint 继续，不叠加 G3/G4/G7；
- PEFT state、FLA、BF16、target-suffix loss、JSONL BOS0、ctx2496、batch1、gradient checkpointing；
- seed1079；2,000 steps；每 250 steps 保存 step250/500/750/1000/1250/1500/1750/2000；
- LR `2e-6 -> 2e-7` cosine；warmup40；Adam beta1=0.9、beta2=0.99、eps=1e-8。

## 固定离线消融与选择

先验证八 checkpoint 的 key/shape/dtype/finite/nonzero、training↔vLLM identity、parent/base/GPU0/state-init。temperature0.1、top-p1、top-k0、单次 raw-first；对每个 checkpoint 完整运行冻结 G4 dev480、G6 dev480 和 G8 holdout240。G6 parent 在 G4/G6 上复用冻结原始证据，在新 holdout 上只运行一次并永久固定。

按 step 从小到大选择第一个同时满足：

1. G4/G6 的 transport、response envelope、schema、operation 均 `480/480`；G8 holdout 四项均 `240/240`；
2. G4 canonical `>=453/480`，关键 operation 不低于 parent：write_file `>=35/40`、write_json `>=31/40`、web_search `>=15/16`、connector_lookup `=16/16`；
3. G6 retention `>=323/336`，clean `72/72`，recovery `72/72`，总计 `>=467/480`；12 个 recovery operation 各自 schema/operation/canonical 100%；retention 净增益为正且网络 row regression=0；
4. 新 G8 holdout canonical `>=231/240`；discount ledger 与 failed-check recovery 各 `>=45/48`；其他三个 workflow family 各不得低于 `46/48`；
5. 三个 eval 的 state attestation、literal request tail、append-only raw journal、first raw envelope 完整；hidden retry=0、postprocessed=false；原始 RWKV token/output 未修改、未删除、未重排、未隐藏。

不得在看到结果后降低门槛、改变相似度算法、增加模型调用，或用 controller/postprocessor 修正参数。若无候选通过，G8 保留为失败证据，不激活。

## Stage B、Stage C 与第一正式版本

只有离线候选通过，才运行 live V1 2/2、V2 6/6、检索质量 9/9、S60 Selector、Executor continuation tail、真实联网与工具落地链。随后在本地 vllm-rwkv 中验证 general/network+workflow 两个 task-level state 的显式绑定、双向交替、缺失/损坏 state 失败关闭、零阶段切换、原始输出不变及延迟门槛。

Stage B/C 通过后，再把该 state 放入“旧 agent 能力增强”真实项目矩阵：项目创建、个人记账网页、中型多文件实现、细致 bug 修复、失败测试恢复和联网查证后修改。正式版本以项目可运行、验收测试通过、旧能力不回归为准，不以训练 loss 或单个示例通过代替。
