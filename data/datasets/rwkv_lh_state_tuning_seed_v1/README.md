# RWKV-LH action state-tuning seed v1

这不是可直接训练的完整语料，而是当前 progressive G1i 协议的合成种子包。

- 版本：`rwkv-lh.action-state-tuning-seed.v1`。
- 种子数：20 个系统行为家族。
- 建议最小扩展量：1824 条已验证 trajectory（按 seed 的
  `minimum_expansions` 求和）。
- 模型职责：RWKV 自己选择 operation、生成完整参数、消费真实 Observation，并决定何时
  `final_answer`。
- Harness 职责：工具注册、参数校验、Network Gate、执行、证据和事件持久化；不可成为训练标签生成器中的语义 Router。

## 文件

- `seed_templates.jsonl`：交给合成器的行为种子；不是最终训练文本。
- `tool_contracts.json`：从当前 ActionHarness 机械导出的 22 个 operation，加
  `final_answer`，用于校验目标参数。
- `SYNTHESIS_PROMPT.md`：可直接交给强模型的扩展指令。
- `manifest.json`：来源、用途、生成方式、摘要、holdout 摘要和污染检查结果。

## 训练数据生成顺序

1. 按 semantic template/entity family 先切分 train/dev；测试集继续使用冻结的
   ECRA route Canary/route120 和 RWKV-E2E-90，不从它们生成训练样本。
2. 使用 `SYNTHESIS_PROMPT.md` 和单个 seed 生成新的 request、workspace fixture、
   Controller event 和 target turn。
3. 用当前 `render_bootstrap`、`render_event_append`、`render_tool_disclosure` 机械渲染
   exact transcript。不要让合成模型仿写 System/Controller 字节。
4. 每个 action turn 生成 selector target 与 direct-call target；Observation 后的 turn
   必须引用真实执行结果，不能引用合成器预期值。
5. 在 sandbox 中实际执行并用 frozen verifier 验收。只收录通过的局部 transaction。
6. 内部去重，并对 holdout request 做 UTF-8 byte 5-gram cosine；最大值必须 `<0.75`。
7. 输出 RWKV 官方 `{"text":"..."}` JSONL，再转换为 binidx。若你的 state-tuning
   管线支持 response loss mask，selector/direct-call/final targets 是监督区；Controller
   prompt 和 tool observations 只作为条件上下文。

## 不得混入

- `rwkv_lh_ecra_route_v1`、RWKV-E2E-90、hidden acceptance、参考答案；
- 历史 `rwkv_lh_operation_selection_v1` 的 `lh_select_operation` target；
- Strong Planner 的 contract-plan JSON；
- failed/false-positive 整条轨迹；
- 未经执行验证的 observation、参数或 completion；
- rationale、分类标签或 Harness 替模型选择的 operation。

官方 RWKV-PEFT 当前 state-tuning 示例使用 `--peft state --op fla`，binidx 输入；
基座 checkpoint、词表、模型代际、`n_layer` 和 `n_embd` 必须与你部署的 13.3B
RWKV-7 严格匹配。训练 `ctx_len` 是数据/显存选择，不是 state 形状身份字段，但必须覆盖你要学习的
多轮 Observation 链；服务端仍可保持当前 16384 context 配置。
