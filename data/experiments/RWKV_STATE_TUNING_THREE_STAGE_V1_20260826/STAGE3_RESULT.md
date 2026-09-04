# Stage 3 结果：自然 connector 已迁移，但联网边界过校准

日期：2026-08-27

## Checkpoint 与训练有效性

- parent 为 Stage1 step 500，SHA-256
  `180fb98e70144d2d078bc3f9c43778c0d7011627c6b5446cfa7783041afd04f8`；
- 唯一预注册选择为 final step 1400，SHA-256
  `ec43842c6c2a22b5d4881daf796d16aeca392dd443cb44b72c3c660c3eebb83b`；
- 61 个 bf16 state tensor 全 finite、nonzero；parent-child cosine
  `0.9668551879`；
- loss 1400/1400 全 finite，first-64 mean `0.0479430798`，last-64 mean
  `9.1940165e-6`；
- 训练/服务 tokenizer 4728 次比较精确率 1.0，BOS 契约 1.0；
- vLLM runtime attestation 确认加载上述 state SHA，方向为
  `rwkv_peft_parameter_v_k_direct`。

## 冻结评价

Round1 dev200：schema 200/200、operation 200/200、arguments exact 186/200；其中 direct
121/121 operation、107/121 arguments exact，selector 79/79。Stage3 natural dev176 为
176/176 operation 和 176/176 exact。两个阶段内门均通过。

ECRA route120 B：

| 类别 | first-tool exact | 预注册门 | 结果 |
|---|---:|---:|---|
| local-only | 27/30 | >=24 | 通过 |
| public-web-required | 21/25 | >=23 | **失败** |
| deterministic-compute | 15/15 | >=14 | 通过 |
| structured-connector | 20/20 | >=12 | 通过 |
| mixed-local-online | 2/20 | >=10 | **失败** |
| privacy-policy-rejection | 2/10 | >=8 | **失败** |

总体 first-tool exact 87/120，expected-sequence prefix 86/120。web/connector macro-F1
`0.903125` 通过；network macro-F1 `0.9188640974` 低于预注册的 `0.944`；local network
false-positive rate `0.30`，未达到 0；required-online FNR `0.0461538` 通过。privacy backend
execution 为 0、policy rejection coverage 为 1.0，均通过。failed/interrupted 8/120，超过
上限 4。

## 判定

Stage3 未通过预注册门，不进入正式部署，环境已恢复到 Stage1 稳定 checkpoint。

训练确实学到了自然 connector 边界：该类从 Stage1 的 0/20 提升到 20/20；但同时把
connector/online 先验推得过强，普通 web 被误分为 connector，本地命令、mixed 和 privacy
任务被过早路由到网络。Stage1 selector replay 保住了 dev200 的停止选择，因此
failed/interrupted 从 Stage2 的 20 降到 8，但仍未恢复 Stage1 的 4。

下一轮应从 Stage1 再起，使用 connector 正例与 ordinary-web/local-only hard negative 的平衡
配对，并把 mixed/privacy 的“读取指定本地依赖后再决定联网”作为自然轨迹主干；不可继续单独
增加 connector 正例或用显式路由提示堆量。
