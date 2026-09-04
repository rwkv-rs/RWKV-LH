# EXE-G7：联网 Executor state 的 workflow 保留能力修复预登记

登记时间：2026-08-29（G7 数据生成、训练、checkpoint 推理和 live V2 运行之前）。

## 目的与架构边界

EXE-G6 已经证明网络 profile 的训练方向有效：最佳观察点 step1500 在冻结 G6 dev480 上达到 clean network-stage `72/72`、protocol-rejection recovery `72/72`，拒绝恢复相对 G4 parent 从 `55/72` 提升到 `72/72`，rescue 17、regression 0。它没有达到发布门，唯一阻塞是 336 条 G4 retention 仅 `310/336`，低于预登记的 `323/336`。

冻结失败分析显示，step1500 的 26 个错误全部为参数精确性错误：schema `336/336`、operation `336/336`；25 个来自多步 workflow，22 个在全部八个 G6 checkpoint 中持续失败。错误集中在长轨迹中的既有值/结构复现：`write_json` 9、`final_answer` 9、`write_file` 4，且 discount ledger 与 failed-check recovery 两类占 21/26。根因是 G6 中完整 workflow 仅占 800/2000（40%），网络/拒绝恢复训练已经饱和，而不是 Selector、工具数量、Harness schema 或检索后端错误。

G7 只修复这个全局分布缺口。它仍是 13.3B Executor 的一个任务级 network profile；不替代 2.9B S60 Selector，不按关键词选择 state，不在 run 的不同阶段切换 state，不叠加多个 state。离线任务仍使用 general profile；`retrieval.mode != offline` 的 run 在 Executor lane 创建时绑定一次 network profile，并在整个 run 中保持 `profile_switches_within_run=0`。

## 冻结证据与输入身份

- G6 ablation result SHA-256：`8ca74af573a0aaae7503e585d4196d70622e8b7bffaa538d5e986c1ad2c0df2e`。
- G6 retention failure analysis SHA-256：`28f1eddaca27cc459f4887f8756c13ed2e38868bc814790b92c5bfa9550177d7`。
- 13.3B base model SHA-256：`5d97772ba04a81bdaeba90e1d6d306c70560bf4f784522be61cdcade69e30562`。
- parent training state：G6 step1500 `rwkv-step-1500.pth`，SHA-256 `648dcdc665ddae69f519718d9b1b6033d354255bfbeeaf9eed6d6a07088c1b78`。
- parent vLLM state：G6 step1500，SHA-256 `611d9e5564ef47413c1bd1536500e987270c8303b2c87d5d54bca256d57dd68b`。
- G4 train / manifest SHA-256：`f5a1e2d3a06c4877bf589001ae988fe4fe7a6a4540e8ca0b5121a8af40890e93` / `ad0781511f2ebc57b30a44dc7cb82daccf43f9871de7d36bcdbd58aeae9c831f`。
- G6 train / manifest SHA-256：`ea3f62b22a6269e8b7d43b71386909532945085ff206d5fa0d530c4fc37519e6` / `b5f960a51a418d45b246bf454a3df8b9c326c0ded66af0e05cb05700a04f3c17`。
- 冻结 G4 eval / manifest SHA-256：`f89ff7828dfa298eedfab6c2cef531708fac7e812e9c309530086a5192770e5d` / `d8dad84b355df504a5162017fedf3fd97036f91485869314187a513b6e71d5cf`。
- 冻结 G6 eval / manifest SHA-256：`f80f7452f5dcc38b8932de50eb391e6b8cbd0f494cbab40b4b8d4b8db6d072ee` / `ba3bb05085c9055b3230fdb79ed859146ddf46d586c8d0f0f3c30b40c810eb3e`。
- V1/V2 live cases SHA-256：`971c89f2def921498b664e069f4af281857aac377bec881ce04d2c57fbb66708` / `d8ad5bd999d26b6b16292fae7503534dcb01d3f8ae0c7a1d9c78c93d1d1deb31`。

不得把 G4/G6 dev、V1 或 V2 的请求、target、RWKV 输出复制进 G7 train。失败分析只允许决定 source kind、operation 和 trajectory-position 的全局配比；不得使用 dev sample ID 或 dev 字面内容构造训练特判。

## 固定 G7 train1200

G7 只从已经冻结并验证过的 G4/G6 **train split** 做确定性 replay，不生成或修改任何 RWKV 文本。每个 prompt 与 target 字节保持源数据不变；只新增 G7 provenance metadata 和 sample ID。

总计 1,200 条：

- 800 条 G4 `synthetic_true_workflow_request_last`：train 中全部保留，每个 family、trajectory 和 position 都保留，不只抽取已知失败位置；
- 240 条 G4 `g3_frozen_direct_retention`：24 个 operation 按 `sample_id` 排序后各取前 10 条；
- 80 条 G6 `clean_network_stage`：`web_search`8、`connector_lookup`8、`write_file`20、`write_json`20、`read_file`6、`read_json`6、`bind_evidence`4、`file_digest`4、`final_answer`4；
- 80 条 G6 `protocol_rejection_recovery`：`write_file`24、`write_json`20、`read_file`6、`read_json`6、`append_file`4、`copy_file`4、`move_file`4、`file_digest`4、`web_search`2、`connector_lookup`2、`bind_evidence`2、`final_answer`2。

因此 retention replay 为 1,040/1,200（86.7%），其中完整 workflow 为 800/1,200（66.7%）；network replay 为 160/1,200（13.3%）。不创建独立 G7 dev，checkpoint 只在上述冻结 G4/G6 eval 上比较。

数据硬约束：

1. exact prompt duplicate 为 0，所有 `text == prompt + target`；
2. prompt、target、target-suffix mask 和 literal request/question tail 与来源逐字一致；
3. ctx2496 下 target truncation 为 0，当前 Harness contract validation 100%；
4. G7 train 与冻结 G4/G6 dev 的 source sample ID overlap 为 0；
5. 对 V1+V2 请求沿用固定 byte 5-gram cosine，最大值 `<0.75`；
6. `generated_rwkv_text=false`、`raw_output_modified=false`，绝不改写、删除、重排或隐藏 RWKV 原始输出。

## 固定训练

- 只在 server physical GPU0；UUID 必须为 `GPU-1faf7f09-25f4-2515-b707-6e0766aa841d`；产品端口 18070 全程保护；
- 从上面的 G6 step1500 **training state** 精确初始化一次，不与 G3/G4/G6 的其他 state 叠加；
- PEFT state、FLA、BF16、target-suffix loss、JSONL BOS 0、ctx2496、batch1、gradient checkpointing；
- seed1071；1,200 steps；每 150 steps 保存，共 step150/300/450/600/750/900/1050/1200；
- LR `1e-6 -> 1e-7` cosine；warmup24；Adam beta1 0.9、beta2 0.99、eps1e-8。

## 固定离线消融与选择

先验证八个 checkpoint 的 tensor key/shape/dtype/finite/nonzero、training↔vLLM identity、base/parent/GPU0/state-init attestation。随后以 temperature0.1、top-p1、top-k0、单次 raw-first，在同一冻结 G4 dev480 与 G6 dev480 上评测。G6 step1500 的已有完整 raw run 作为 parent 基线，不重跑、不替换。

按步数从小到大选择第一个同时满足：

1. 两个 dev 的 transport、response envelope、schema 和 selected operation 均 `480/480`；
2. G4 dev canonical exact `>=453/480`；关键 operation 不低于 parent：`write_file>=35/40`、`write_json>=31/40`、`web_search>=15/16`、`connector_lookup=16/16`；
3. G6 retention canonical exact `>=323/336`；
4. G6 clean network-stage 必须保持 `72/72`，protocol-rejection recovery 必须保持 `72/72`，因此 G6 total 必须 `>=467/480`；
5. recovery 的 12 个 operation 每个都 schema、operation、canonical exact 100%；
6. 相对 G6 step1500，retention 净提升为正；clean/recovery row-level regression 为 0；
7. 两个 eval 的 state attestation、request/question-at-tail、append-only raw journal 和 first raw output 完整；hidden retry=0、postprocessed=false、原始 RWKV token/output 未修改、未删除、未重排、未隐藏。

任何 checkpoint 未通过都不得激活；不得在看到结果后降低门槛、改变相似度算法、增加模型调用或用 controller/postprocessor 修正参数。

## Stage B / Stage C 与发布门

只有离线候选通过后，才为 G7 单独冻结 Stage B runner：历史 live V1 2/2、尚未执行推理的 V2 6/6、检索质量 9/9 hard gates、相关 Harness 回归和 Full90 dispatch/integrity。随后在同一 13.3B vLLM-rwkv engine 中验证 general 与 network profile 的显式 run-level 绑定、各自独立 state、零阶段切换及连续切换压测；任何响应都必须保留原始 RWKV 输出与 state attestation。

Stage B/C 任一失败时，G7 不写入 `.env.local`，`RWKV_EXECUTOR_PROFILE_ROUTING` 保持 `disabled`，生产 G3 和当前联网路径保持不变。
