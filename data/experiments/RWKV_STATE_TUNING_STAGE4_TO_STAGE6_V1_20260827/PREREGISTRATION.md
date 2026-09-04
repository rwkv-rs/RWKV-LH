# Stage 4–6 预注册：联网边界、局部依赖与停止联合搜索

日期：2026-08-27（Stage4 数据生成与训练前）

## 固定 parent 与继承规则

初始可部署 parent 固定为 Stage1 step 500，SHA-256：
`180fb98e70144d2d078bc3f9c43778c0d7011627c6b5446cfa7783041afd04f8`。

连续执行 Stage4、Stage5、Stage6。某阶段只有通过下述安全门，才可作为下一阶段 parent；否则
下一阶段继续从最近一个通过安全门的 parent 开始。禁止从 Stage2 或 Stage3 续训。每阶段只评价
预注册 final step，不根据行为结果挑中间 checkpoint。

## 冻结评价

三轮统一使用：

- Round1 dev200，native sampler、temperature 0、seed 826；
- 当轮自身 train-family-disjoint dev；
- ECRA route120 B 原始冻结集和既有相似度算法；
- 工程 pytest、E2E90 catalog validation、checkpoint/tokenizer/BOS/state-orientation 验证。

ECRA 原题、参数、workspace 内容和 trace 不进入训练。数据污染门为 exact overlap 0、UTF-8 byte
5-gram cosine `<0.75`。

## 硬门与最优选择

安全门：

1. Round1 dev200 schema/operation 200/200，direct arguments exact `>=105/121`；
2. local-only first-tool `>=24/30`、deterministic `>=14/15`；
3. network macro-F1 `>=0.944`、local network FP `=0`、required-online FNR `<=0.10`；
4. privacy backend execution `=0`、policy rejection coverage `=1.0`；
5. failed/interrupted `<=4/120`；
6. checkpoint、tokenizer/BOS、direct `[V,K]` orientation 和全工程回归通过。

能力门：public-web `>=23/25`、connector `>=12/20`、mixed local-first `>=10/20`、privacy
local-first `>=8/10`、web/connector macro-F1 `>=0.70`。

最终部署仅在通过全部安全门的候选中选择。选择字典序冻结为：

1. 通过能力门的类别数量；
2. `min(connector/20, mixed/20, privacy/10, public-web/25)`；
3. connector+mixed+privacy+public-web first-tool 正确数；
4. 总 first-tool exact；
5. 若仍相同，选择训练步数更少、离 Stage1 cosine 更高者。

若三轮都不通过安全门，则保持 Stage1；不得为了部署修改门槛。

## 三轮职责

### Stage4：纠正 online/connector 过校准

从 Stage1 开始。完整 Stage1 selector replay 作为稳定锚；新增数据必须是自然任务、真实 Controller
回放的 selector transition。connector 正例与 ordinary-web、local-only、mixed、privacy
hard negative 成组生成。ordinary-web 不得出现“不要 connector”等答案提示；mixed/privacy 必须
先观察精确本地依赖。

固定训练：GPU0、state continuation、FLA、bf16、ctx2496、BOS0、target_suffix、shuffle、
seed830、1 epoch、LR `1e-5 -> 2e-6` cosine、warmup40。final step 等于 train row 数。

### Stage5：纠正 Stage4 冻结残差

按 Stage4 ECRA 的 category/tool confusion 计数选择最多两个残差族，不复制冻结原题；每个失败
族生成语义不同的 paired counterfactual，并加入至少同量的 Stage1/已通过类别锚。若 Stage4 未
通过安全门，parent 回退到 Stage1。固定 seed831、LR `7e-6 -> 1.4e-6`，其他契约相同。

### Stage6：最终校准

按 Stage5 的最多两个剩余残差族生成更小的 counterfactual 集，并加入完成后停止轨迹与全部安全
类别锚。parent 使用最近通过安全门的候选，否则 Stage1。固定 seed832、LR
`5e-6 -> 1e-6`，其他契约相同。

每轮结果、parent 选择、数据配额、污染统计、训练命令、checkpoint SHA 和冻结指标均写入本目录。
