# Local Dual-Model State Profiles v1 — 预注册协议

## 状态与目标

- 登记时间：2026-08-28（Asia/Shanghai）
- 当前状态：架构与引擎基础能力实现中；训练、canary、Full90 均未开始
- 目标：把工具选择与工具执行彻底分离，并用固定消融确定满足质量门槛的最少 state-tuning profile 数量
- 正式候选：2.9B RWKV Selector + Hidden/MLP exact-tool head；13.3B RWKV Executor
- 推理后端：项目固定的本地 `vllm-rwkv`，Selector 与 Executor 使用同一套数值执行配置，模型尺寸、服务端口、并发上限和 profile manifest 按角色分别登记

运行后不得改变数据集、split、阈值、相似度算法、采样参数或评价器来改善结果。任何变化必须登记为下一协议版本并完整重跑所有对照。

## 不可违反的原始输出合同

1. 不得使用 constrained/guided decoding、`allowed_token_ids`、`bad_words`、`logit_bias`、结构化输出 grammar、隐藏重试或输出 repair 诱导 Executor 产出指定答案。
2. Executor 返回的原始文本、token IDs、finish reason、response/model identity、采样参数、profile identity 和 UTF-8 SHA-256 必须先作为只追加事实保存，再进行解析。
3. parser 只能产生派生视图。解析失败只能拒绝该候选；不得改写、截断、补全或删除原始输出。后续协议拒绝是新的显式 causal event，不覆盖旧输出。
4. Selector 不生成工具调用文本。其原始产物定义为完整分类 logits、选择类别、置信度、head/profile/model digest；这些字段同样不可修改。
5. UI、benchmark 和导出同时保留 raw 与 derived 字段，且不得把 derived 字段标记为 RWKV 原始输出。
6. 原始输出完整性是硬门槛：server response → runtime audit → causal event 三处 UTF-8 SHA-256 必须 100% 一致；任一缺失或不一致使整次运行无效。

## 固定拓扑

```text
append-only CausalEvent authority
           ├─ Selector projection -> 2.9B + selector state -> Hidden/MLP
           │                                      └─ selection_id + exact tool
           └─ Executor projection -> 13.3B + executor state -> raw op/args/final
                                                  └─ Harness mechanical gate
```

### Selector

- 只接收任务意图、当前阶段目标、20 个冻结类别的名称/一句描述和紧凑 causal progress。
- 20 类固定为当前 18 个 Harness operation、`final_answer`、`ABSTAIN`。
- 不接收参数 Schema、工具用法长文、长工具结果、Executor 原始推理或答案参考。
- Hidden/MLP 候选使用最后一个真实输入 token 的 final hidden；WKV-statistics + train-only PCA + MLP 仅作为预注册特征消融，不得测试后选择新 pooling 口径。
- Selector 的 run-local recurrent state 持续存在；每一步 append 新 selector projection，不从 Executor transcript 重建，也不在每个步骤重载 initial state。

### Executor

- 接收精确执行目标、已提交的 operation、该 operation 的完整 Schema/用法，以及完成本次参数绑定所需的原始 observation。
- 不接收 Selector logits、置信度解释或 Selector 隐藏状态。
- 13.3B 只生成原始 operation arguments 或 final text；Harness 只做机械协议/安全/权限校验。
- Executor 的 run-local recurrent state 持续存在；Selector/Executor state 永不互相导入。

### Handoff 与恢复

- `selection_id` 必须先作为 causal event 提交，再允许 Executor 生成。
- `selection_id` 绑定 selector checkpoint、executor parent checkpoint、tool definition digest、两个 profile digest 和输入 projection digest。
- 崩溃恢复必须复用已提交选择；不得因为重启再次选择同一步工具。
- lane checkpoint 必须记录 base model、engine build、profile ID/SHA、state digest、parent、token position 和 export format。任一身份不一致时 fail-closed。

## vllm-rwkv 固定实现边界

- 基础提交：`67f0c5996c50dca0ad779da545cb491527de988f`。
- 初始 state profile 在服务启动时按 manifest SHA-256 和每个 state SHA-256 一次性预加载。
- 请求只能通过 `vllm_xargs.rwkv_state_profile` 和 `rwkv_state_profile_sha256` 选择已注册 ID/摘要；不能提供文件路径，且请求摘要与服务注册摘要不一致时必须在 state row 分配前拒绝。
- profile 选择发生在 state row 分配前。未知 ID、重复 ID、模型身份、key set、shape、BF16 dtype、PP/TP partition 或 digest 不符全部拒绝。
- manifest 的默认 profile 固定为 `zero`；所有 tuned profile 必须由请求显式携带 ID 与摘要，禁止服务端静默套用未被上层审计的 tuned state。
- prefix/recurrent cache identity 必须包含 profile ID 和 profile SHA；不同 profile 不得复用相同 token prefix 的 state。
- 不允许通过进程级环境变量热切换 profile；这会让并发请求串 state。
- 本协议不把 prompt replay 或普通 prefix cache 称为 durable recurrent state。create/resume/fork/commit/rollback/export/import 全合同完成前，上层必须继续如实标记 transport。

固定数值配置沿用现有高质量服务：Model Runner V2、`VLLM_RWKV7_WKV_MODE=fp32io16`、同一 tokenizer/build、`max_model_len=16384`。每次正式运行必须把完整命令、环境白名单、GPU、Torch/CUDA、engine commit/diff digest、模型和 profile SHA 写入产物。

## 模型与数据冻结

### 模型

- Selector base：`rwkv7-g1i-2.9b-20260805-ctx16384.pth`，字节数 `5896273469`，SHA-256 `ac1ae23d0e65c1d35ba523eacd81a2a4dacb7b886479909bbff34f312e766320`。
- Executor base：`rwkv7-g1i-13.3b-20260805-ctx16384.pth`，正式运行前复核既有 SHA-256 `5d97772ba04a81bdaeba90e1d6d306c70560bf4f784522be61cdcade69e30562`。
- Selector state、MLP head、PCA（若启用）和 Executor state 都必须各有独立 manifest 和 SHA-256。
- 任何未登记 artifact 都不能进入正式消融。

### Selector 数据集

必须在第一次训练前生成并冻结 `rwkv_lh_exact_tool_selector_v1`：

- 来源只允许当前 18-tool registry、成功的真实 Controller pre-action state、失败/恢复轨迹和 final boundary；历史人工 operation-selection 30 例只用于 smoke，不计正式指标。
- label 由已成功执行并通过 verifier 的下一 operation、已验收 final 或机械 `ABSTAIN` 产生；不得由待评模型自标。
- split 按任务/语义 family，而不是按行随机；同源变体只能位于一个 split。
- 使用已登记的 `utf8-byte-5gram-cosine.v1`，阈值 `0.95` 去重。比较对象固定为 canonical `task_request + stage_objective + stage_role + compact progress`，不包含每行完全相同的 20-tool menu；仅在同 label 内删除重复。跨 label 近邻是 state 边界对照，必须保留、单独登记，并由 family split 保证不跨 split。
- 数据同时保存未去重的完整 causal trajectory。特征提取固定为每条 trajectory 只加载一次 Selector initial profile，然后按 `trajectory_step_index` 依次 append `SelectorStep`；候选行只控制哪些 step 进入 head loss，不能逐行重载 profile 或从 zero 独立提取来代替正式口径。
- 冻结后记录 source/version/purpose/generation、每类计数和所有文件 SHA-256。
- 固定 train/dev/test 比例 `80/10/10`；正式 test 至少每类 30 例，不足时不得报告毕业结论。

### 端到端数据集

固定 Full90，不重新生成：

| 文件 | SHA-256 |
|---|---|
| `benchmarks/rwkv_e2e/rwkv_e2e_30/tasks.json` | `0bf73c9a86bd014f5a94e5686ffe744bbef6c560f4227e37d0b753b900481c4c` |
| `benchmarks/rwkv_e2e/rwkv_e2e_30/acceptance.json` | `c4953c556a9ba2e080493f34bb2261db349080542376c4e94f08d5227e0f74cd` |
| `benchmarks/rwkv_e2e/rwkv_e2e_lh12/tasks.json` | `d813a7bc3a42e27ee3573ea342a918bd7ee5347ca8b0e893c04fded262457a5e` |
| `benchmarks/rwkv_e2e/rwkv_e2e_lh12/acceptance.json` | `976e075bcc81780ed38ce7b9fe8c6c19c1b239bb72595ce176308f2760a0cd9f` |
| `benchmarks/rwkv_e2e/rwkv_e2e_extension48/tasks.json` | `384d52b5395dbcb31947dbfd1cfe63167ccbe68ed8b03e675fddc32ffd25ec7b` |
| `benchmarks/rwkv_e2e/rwkv_e2e_extension48/acceptance.json` | `395e1651f52259de7e56a63476504891f136edd2d4dd5a8263064077741ede12` |

## 固定消融

所有组使用相同 engine build、数值配置、任务顺序、外部 verifier、并发、超时和采样配置。

- R0：当前 13.3B 同一生成 lane 完成选择与执行，作为历史/同机基线。
- A：2.9B Selector profile + exact-tool MLP；13.3B 单一 Executor profile。默认正式候选。
- B：A + 独立 final Executor profile，共 3 个 profile。
- C：B + 独立 recovery Selector profile，共 4 个 profile。
- L0：0.4B Selector 替代 2.9B，其余同 A，只作为速度/容量下界，不作为默认蒸馏路径。
- F1：2.9B last-hidden + MLP。
- F2：2.9B WKV statistics + frozen train-only PCA + MLP。

选择规则按顺序执行：先比较 F1/F2，固定胜者；再按 A→B→C 增加 profile。只有当前组在完整 test 和 Full90 上存在同源、可复现的残余错误，并且下一组解决该错误而不增加 handoff/完整性错误时，才保留新增 profile。若两组 Strict 相差不超过 1 题且均过硬门槛，固定选择 profile 更少的一组。

## 固定指标与门槛

### Selector 离线

- exact-tool accuracy `>= 0.97`
- macro-F1 `>= 0.95`
- 非 final 样本 early-final rate `<= 0.005`
- 应选择工具样本 false-ABSTAIN rate `<= 0.01`
- ECE（15 个等宽 bin）`<= 0.03`
- unknown/OOD 集 `ABSTAIN >= 0.95`
- 同一冻结输入重复 3 次的 logits/类别必须 byte-identical

### 端到端质量

- canary 固定 `B01,B02,B10,M03,M12,H10`，所有组必须 6/6 transport/protocol valid 才能进入 Full90。
- Full90 必须 90/90 valid；Strict 不低于同机 R0，且不得低于历史 36；FP 不高于同机 R0 且 `<=30`；FN 不高于同机 R0 且 `<=1`。
- selector→executor handoff mismatch、crash-resume reselection、profile/cross-run state contamination 均必须为 0。
- 原始输出三段 SHA 一致率必须 100%；forbidden decoding field 计数必须为 0；非法候选 raw retention 必须 100%。
- 全部文件/JSON/verifier、网络策略、幂等、异常、恢复和历史回归必须通过。

### 性能服务

- 报告 Selector/Executor 各自 TTFT、tokens/s、每步 wall time、队列时间、GPU memory、CPU offload、state copy/restore 时间和总任务 wall time的 p50/p95。
- A 的选择阶段 p95 必须低于 R0；A 的 Full90 总 wall-time p95 不得比 R0 恶化超过 10%。
- 质量门槛优先；吞吐或成本不能补偿 Strict、完整性或安全失败。
- 固定并发阶梯 `1, 4, 8, 16`；每级预热 10 请求、计量 100 请求。发生 OOM、state 串线或输出 digest 缺失即失败。

## 验证顺序

1. engine 单元测试：manifest/profile/hash/shape/dtype/PP/TP、row 生命周期、prefix cache 隔离、并发混合 profile。
2. engine 真实模型 parity：zero profile 与未启用 profile 的 logits/token byte exact；同一 tuned profile 与冻结单-profile adapter 的 logits/token byte exact。
3. 原始输出完整性与 causal recovery 测试。
4. Selector 冻结 test 全量。
5. 固定 canary。
6. Full90 首跑与同条件确认复跑。
7. 并发性能阶梯和长时稳定性。

在以上全部完成前，只能报告“基础能力/某阶段通过”，不得标记整体方案已解决或投入正式建议模式。
