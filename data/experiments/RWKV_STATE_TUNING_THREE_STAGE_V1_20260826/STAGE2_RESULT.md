# Stage 2 结果：合成边界满分但跨措辞迁移失败

日期：2026-08-26

## Checkpoint 与训练有效性

- final step 640 SHA-256：`baa948e46ca98eede3653fdce3efe3c9073148604043b5b23cc8ef46fbf12809`；
- 61 个 bf16 state tensor 全 finite、nonzero；parent-child cosine `0.9844826277`；
- loss 640/640，first-64 mean `0.0289809089`，last-64 mean `4.9269293e-6`；
- 训练/服务 tokenizer 2208 次比较精确率 1.0，BOS 契约 1.0；
- vLLM attestation 确认 direct `[V,K]` state 方向。

## 冻结评价

Stage2 自身 synthetic dev96 为 96/96 operation、96/96 exact，说明优化目标已被学习；但
frozen Round1 dev200 从 Stage1 的 200/200 operation 回归为 197/200。三个回归均为
`completion_evidence` selector：期望 `final_answer`，实际 `read_json`。

ECRA route120 B：

- first-tool exact 76/120（Stage1 为 58/120）；
- local-only 26/30（原 20/30）、public-web 25/25（原 23/25）、deterministic 15/15
  （原 14/15）；
- structured connector 0/20，全部仍为 `web_search`；
- mixed local-first 5/20，privacy local-first 5/10；
- network macro-F1 `0.9825123871`，但 local network FP `0.0666667`；
- failed/interrupted 20/120（原 4/120），主要是动作完成后重复相同工具，未转
  `final_answer`。

## 判定

Stage2 未通过预注册门，不作为 Stage3 parent。根因不是 checkpoint 未生效：synthetic dev96
满分且多个 ECRA 类别有显著变化。根因是数据存在两个系统性捷径：connector 样本显式写出
“选择 structured connector 而不是 web”，没有覆盖自然用户问法；local-first 正例过多而
完成边界回放不足，造成“继续观察本地”压过“证据充分后停止”。

Stage3 从 Stage1 稳定 checkpoint 重新开始，使用自然 connector 问法并混入完整 Stage1
selector replay 作为抗回归锚点。
