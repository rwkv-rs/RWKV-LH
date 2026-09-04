# Stage 3 预注册：自然路由迁移与停止边界联合校准

日期：2026-08-26（数据生成与训练前）

## 入口状态与目标

Stage2 checkpoint 通过数值、tokenizer 和部署验证，但未通过行为门，因此按 Stage2 预注册
规则不作为 parent。Stage3 固定从 Stage1 step 500 开始，parent SHA-256：
`180fb98e70144d2d078bc3f9c43778c0d7011627c6b5446cfa7783041afd04f8`。

本阶段只修复 Stage2 已证实的两个系统性问题：

1. connector 合成样本依赖显式“选 connector/不要 web”措辞，synthetic dev 满分却在自然
   ECRA 问法 0/20；
2. local-first 强化造成完成后重复动作，Round1 completion selector 回归 3 条，ECRA
   interrupted 从 4 增至 20。

## 冻结数据协议

版本 `rwkv-lh.state-tuning.stage3-natural-route-stop.v1`，train 1400：

- `stable_selector_replay` 500：完整复用 Stage1 train selector（仅 train，不含其 79 条 dev），
  保留 completion、no-progress、observation、coverage 和 privacy 边界；
- `natural_connector` 400：100 个 semantic family × 4 surface variants，均为自然查询，不得
  出现“选择 connector”“不要 web search”等路由答案提示；覆盖 8 个 connector operation；
- `ordinary_web` 100：25 family × 4，用自然普通网页需求作为 connector hard negative；
- `mixed_local_first` 200：50 family × 4；
- `privacy_local_first` 200：50 family × 4。

新增 dev 176：natural connector 64、ordinary web 16、mixed 48、privacy 48。train/dev family
严格不相交；ECRA120、E2E90 的原题、参数、trace 和 final wording 不进入训练。固定 UTF-8
byte 5-gram cosine `<0.75`、exact overlap 0。所有新增轨迹由当前 Controller、ModelSession、
ActionHarness 与冻结 backend 真回放；target 仅监督 selector transition，不训练任务答案。

## 冻结训练参数

- GPU0；state continuation；`--op fla`；bf16；ctx 2496；BOS 0；target_suffix；
- 1400 steps、1 epoch、shuffle、seed 829；
- LR `2e-5 -> 4e-6` cosine、warmup 40；
- step save 350；唯一选择 final step 1400，不按行为结果挑中间 checkpoint。

## 固定评价与通过门

同一 native sampler、temperature 0、seed 826：

1. Round1 dev200 schema/operation 200/200，direct exact arguments 至少 105/121；
2. Stage3 自身 natural dev operation 至少 170/176；
3. ECRA connector first-tool 至少 12/20，mixed local-first 至少 10/20，privacy local-first
   至少 8/10；
4. local-only first-tool 至少 24/30，public-web 至少 23/25，deterministic 至少 14/15；
5. web/connector macro-F1 至少 0.70；network macro-F1 至少 0.944；local network FP 0；
   required-online FNR 不高于 0.10；
6. privacy backend execution 0、policy rejection coverage 1.0；
7. failed/interrupted 不多于 4/120；
8. checkpoint、tokenizer/BOS、state orientation 和全工程回归全部通过。

若任何门失败，三阶段实验仍按事实完成，但正式部署恢复 Stage1 稳定 checkpoint，失败结果作为
下一轮 state-tuning 数据合成依据，不临时改变阈值或挑 checkpoint。
