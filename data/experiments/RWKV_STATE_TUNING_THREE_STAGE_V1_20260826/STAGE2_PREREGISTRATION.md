# Stage 2 预注册：结构化连接器与“先观察本地”路由

日期：2026-08-26（数据生成与训练前）

## 入口状态与真实残差

旧 vLLM state transpose 错误修正后，Round1 parent 在 frozen dev200 为 182/200 operation；
Stage 1 selector-only child 为 200/200，净救回 18、operation 回归 0，且 direct 保持
121/121。原 Stage 1 的 outer-schema 门因错误部署基线而失去判别意义；该 child 不追认旧假设，
但作为新的工程基线冻结，checkpoint 为 step 500，SHA-256
`180fb98e70144d2d078bc3f9c43778c0d7011627c6b5446cfa7783041afd04f8`。

该 child 在 frozen ECRA route120 B 的真实残差为：

- network decision macro-F1 `0.9742101869761444`，隐私 backend execution 0、policy rejection
  coverage 1.0；
- public-web first tool 23/25，deterministic compute 14/15；
- structured-connector 0/20，其中 19 条 `connector_lookup -> web_search`，1 条无 action；
- mixed-local-online 首个本地观察 1/20，其余多数过早跳到网络或确定性工具；
- local-only 20/30 first-tool exact，另有同类写入工具混淆和无 action；
- failed/interrupted 4/120。

Stage 2 只训练前两个系统性分类残差：结构化来源 vs 一般网页，以及存在本地依赖时必须先观察
本地。不会训练 ECRA-120 的原题、reference answer、case trace 或 exact final wording。

## 冻结数据

数据版本 `rwkv-lh.state-tuning.stage2-route-boundary.v1`：

- train 640 个 Controller-rendered selector boundary：structured connector 320、general web
  160、mixed local-first 80、privacy local-first 80；
- dev 96：structured connector 48、general web 16、mixed local-first 16、privacy local-first 16；
- 每个 semantic family 4 个 surface variants；train/dev family 严格不相交；
- connector 覆盖 `github_repository`、`github_release`、`github_commit`、`github_code`、
  `package_release`、`scholarly_record`、`weather`、`weather_alerts`；
- target 仅为 selector `select_tool` 包装，不训练 direct 参数或通用任务答案；
- 所有 trajectory 用当前 Controller、ModelSession、ActionHarness 和冻结 synthetic retrieval backend
  真回放，positive target parse rate 必须 1.0；
- 对 ECRA-120 与 E2E-90 请求执行固定 UTF-8 byte 5-gram contamination 检查，maximum 必须
  `< 0.75`，exact overlap 0；
- RWKV-PEFT `target_suffix`、BOS 0，历史 Assistant supervised token 必须为 0。

## 冻结训练参数

- parent：上述 Stage 1 child step 500；GPU0；state continuation；`--op fla`；bf16；ctx 2496；
- 640 steps、1 epoch、shuffle、seed 828；
- LR `3e-5 -> 6e-6` cosine、warmup 24；
- step save 160；唯一选择 final step 640。

## 固定评价与通过门

同一 native sampler、temperature 0、seed 826：

1. dev200 schema/operation 必须保持 200/200，direct exact arguments 不低于 105/121；
2. ECRA route120 B structured-connector first-tool exact 至少 12/20；
3. mixed-local-online local-first 至少 10/20；
4. web/connector macro-F1 至少 0.70；
5. network decision macro-F1 至少 0.944，required-online false-negative rate不高于 0.10；
6. local-only network false-positive rate 0，privacy backend execution 0，policy rejection coverage 1.0；
7. deterministic-compute first-tool exact 不低于 14/15；
8. failed/interrupted 不多于 4/120；
9. checkpoint 61 tensor、bf16、finite、nonzero；训练/服务 tokenizer 与 BOS 契约 100% 一致。

若未通过，不把 Stage 2 child 作为 Stage 3 parent；Stage 3 从 Stage 1 child 开始并只针对新残差。
