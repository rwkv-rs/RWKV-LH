# RWKV Action State Tuning 10K v1 预注册

> **状态：已中止，不得用于训练或正式实验。** 该版本用语义模板组合满足数量与
> 相似度指标，却没有把已观测故障作为每条样本的直接来源。中止证据与影响范围见
> `ABORTED.md`；后续由 failure-grounded 版本取代。

日期：2026-08-26（Asia/Shanghai）

## 用户修正后的交付口径

最终可训练 `{"text":"..."}` JSONL 必须恰好 10,000 条，而不是把 480 条 Phase-A
trajectory 当作正式规模。计数单位固定为一次真实模型 generation 的监督 stage：

- progressive selector 是 1 条；
- contract 披露后的 direct call 是 1 条；
- 协议拒绝后复用已披露合同的 corrected direct call 是 1 条，不伪造第二次 selector；
- malformed、prelude 和仅为终止回放增加的 postlude 不进入正向计数。

目标固定为 9,000 train + 1,000 dev，合计恰好 10,000。

## 来源与边界

继续使用 `rwkv-lh.action-state-tuning-seed.v1` 的 20 个 seed 和当前 authoritative
ActionHarness contracts。复用 `/home/chase/GitHub/RWKV-state-factory` 的私有 oracle、冻结环境
回放、verifier-only acceptance、family split 和污染闸门方法，但不复用其 Web schema、verifier、
renderer 或污染算法。

480-trajectory 包只作为生成链 pilot，不直接复制或重复进 10K 包。10K 中每条 trajectory 都创建
独立语义 family/variant、workspace fixture 和真实 Controller replay。

## 精确计数构造

每个 seed 的单 trajectory 正向 stage 权重固定为：

| seed | stage/trajectory |
|---|---:|
| ST-ACT-001--010 | 2 |
| ST-ACT-011--012 | 4 |
| ST-ACT-013--014 | 6 |
| ST-ACT-015 | 4 |
| ST-ACT-016 | 1 |
| ST-ACT-017 | 2 |
| ST-ACT-018 | 8 |
| ST-ACT-019 | 2 |
| ST-ACT-020 | 4 |

20 个 seed 各一条 trajectory 的 stage 总权重为 61。

train 构造：

- 先给每个 seed 148 条，得到 `61 * 148 = 9028` stage；
- ST-ACT-001--010、017、019 各减 1 条，共减 24 stage；
- ST-ACT-011 再减 1 条，共减 4 stage；
- 最终恰好 9000 stage。

dev 构造：

- 每个 seed 16 条，得到 `61 * 16 = 976` stage；
- ST-ACT-013 增加 4 条，增加 24 stage；
- 最终恰好 1000 stage。

最终共 3271 条 verified trajectory：2947 train / 324 dev。

## family 切分

- semantic family 最多 4 个 surface/argument variant；最后一个 family 可为 3 个 variant。
- train/dev 使用不相交 family ID 和不相交实体命名空间。
- 预计 821 个 semantic family：740 train / 81 dev。
- 不允许同一 trajectory 或同一 family 跨 split。
- 不允许通过重复同一个 `text` 行补足 10K。

## 固定生成与验收

每条 trajectory 都必须：

1. 使用独立 request、参数实体和 workspace fixture；
2. 通过当前 progressive `LongHorizonController`、`LongHorizonModel`、`ModelSession` 和
   `ActionHarness` fresh replay；
3. 网络成功样本只使用冻结 `.invalid` evidence，生成时不得真实联网；
4. Gate 隐私样本后端执行数为 0，参数不重写、不重试；
5. Observation literal binding、协议纠错、provider unavailable、mutation fresh read 和完成边界
   由 frozen verifier 检查；
6. 失败或 malformed 只进入 rejected/filter 文件；
7. 每个正向 prompt 必须是实际 ModelSession generation 边界的原始字节；
8. target 必须通过当前 selector/direct parser 和 authoritative contract。

允许修复生成器根因后重跑全部同类数据，不允许降低验收口径或为单条用例特判。

## 固定数据闸门

- official SFT：恰好 10,000；train/dev 恰好 9,000/1,000；
- verified trajectory：恰好 3271；train/dev 恰好 2947/324；
- accepted rate：100%；positive target parse rate：100%；
- official `text` exact duplicate：0；request exact duplicate：0；
- train/dev semantic-family overlap：0；
- 对冻结 210 条 holdout 的 UTF-8 byte 5-gram cosine 最大值严格 `<0.75`；
- 跨 semantic family request cosine 最大值严格 `<0.75`；
- privacy backend execution count：0；
- 真实 secret、credential、private key、holdout reference answer：0。

## 导出

输出 `data/datasets/rwkv_lh_action_state_tuning_10k_v1/`：

- `rwkv_state_tuning.train.jsonl`：9000；
- `rwkv_state_tuning.dev.jsonl`：1000；
- stage audit train/dev；
- semantic candidates；
- private oracle trajectories；
- validations、rejected attempts、manifest、README；
- 全文件 SHA-256 与字节数。
