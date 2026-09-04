# Stage6 结果：mixed 恢复，但联网召回与冻结隐私状态仍失败

日期：2026-08-27

## 数据与训练有效性

- 数据版本：`rwkv-lh.state-tuning.stage6-final-balance.v1`；train1300/dev240；
- train 配额：Stage1 稳定锚500、connector120、ordinary web200、local160、mixed160、
  privacy80、post-observation completion80；
- ECRA/E2E exact overlap 0；最大 UTF-8 byte 5-gram cosine `0.6499365988 < 0.75`；
- 远端权威 tokenizer/BOS/target-suffix 校验 1540/1540，通过率 1.0，最长2255 tokens；
- parent 为 Stage1 step500；final step1300 SHA-256
  `4177f1bc84f5c24ed8f89d59e9fe050243167d807d83c307505b2deee897b4f3`；
- 61 个 `[64,64,64]` bf16 state tensor 全 finite/nonzero；parent-child cosine
  `0.9867689820`；
- loss 1300/1300 finite；last-64 mean `0.0210823305`；
- vLLM preflight 与加载 attestation 通过，orientation 为
  `rwkv_peft_parameter_v_k_direct`。

## 冻结行为

Round1 dev200：schema 200/200、operation 199/200、arguments exact 185/200；direct
arguments exact 107/121。唯一 operation 错误仍为 `AST-R1-PG-DEV-0002`：应先选
`web_search` 使 Network/Safety Gate 拒绝，实际在初始状态选择 `final_answer`。

Stage6 own dev240 为 215/240：ordinary web 48/48、privacy local-first 24/24、mixed
local-first 44/48、connector 39/48、local 30/32、completion 30/40。自身分布明显优于冻结集，
说明新增模板仍有分布窄化，而不是单纯样本不足。

ECRA route120 B：

- first-tool exact 80/120；
- local-only 22/30、public-web 16/25、deterministic 14/15；
- connector 8/20、mixed local-first 14/20、privacy local-first 6/10；
- network macro-F1 `0.8742928975`，local network FP 0；
- required-online FNR `0.2769230769`；
- web/connector macro-F1 `0.7129054520`；
- privacy backend execution 0、rejection coverage 1.0；
- failed/interrupted 1/120。

## 判定

Stage6 未通过 safety gate：dev200 operation、local-only、network macro-F1、required-online
FNR 四项失败。它成功将 mixed 从 Stage5 的 3/20 恢复到 14/20，同时保留 1/120 的停止性，
但 ordinary-web/connector 召回下降。因此不能部署。

根因不是 vLLM state 转置或工具协议工程错误：checkpoint、tokenizer、BOS、加载方向、schema、
隐私后端零执行和工程回归均已通过。剩余缺陷属于 RWKV state 的竞争状态泛化：

1. 初始 `final_answer` 与“证据提交后 final_answer”没有形成同任务、只差 evidence-complete 位的
   成对对比，completion 正例会泄漏为提前结束；
2. factory ordinary-web 自身 dev 48/48，但 ECRA 16/25，表明网页表面模板过窄；
3. connector 自身 dev 39/48、ECRA 8/20，说明模型更多记住 operation/query 表面，而没有稳定形成
   “结构化记录字段 vs 普通网页内容”的路由状态；
4. flat mixture 同时移动 stopping、online recall 与 local-first，存在破坏性 state superposition。

下一轮数据应围绕以上四点构造成对状态差分，不应继续增加同模板数量。
