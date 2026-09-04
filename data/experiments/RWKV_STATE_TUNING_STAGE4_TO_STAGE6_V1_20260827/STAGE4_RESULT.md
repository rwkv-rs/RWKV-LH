# Stage4 结果：局部依赖迁移成功，停止门仍失败

日期：2026-08-27

## 有效性

- parent：Stage1 step500，SHA
  `180fb98e70144d2d078bc3f9c43778c0d7011627c6b5446cfa7783041afd04f8`；
- final step1140，SHA
  `8af6f29bb8cd68ed2f5e7ca6bcee56f7df7c53bccb083a80d1fa51e680d81960`；
- 61 个 state tensor 全 finite/nonzero，parent-child cosine `0.9785969214`；
- 1140 条 loss 全 finite，最后 285 steps mean `0.0035964652`；
- tokenizer/BOS/target-suffix、direct `[V,K]` runtime attestation 全通过；
- 工程回归 315 passed，E2E90 catalog 90/90，`git diff --check` 通过。

## 冻结行为

Round1 dev200 schema/operation 200/200，direct arguments exact 107/121。Stage4 自身 dev240
为 234/240；6 个错误全部是 natural connector 中 GitHub exact-file 形态被误选为 `read_file`。

ECRA route120 B：

- first-tool exact 100/120；
- local-only 26/30、public-web 22/25、deterministic 15/15；
- structured connector 11/20、mixed local-first 17/20、privacy local-first 9/10；
- network macro-F1 `0.9742101870`，local network FP `0`，required-online FNR
  `0.0923077`；
- web/connector macro-F1 `0.8044217687`；
- privacy backend execution 0、rejection coverage 1.0；
- failed/interrupted 9/120。

## 判定与 Stage5 输入

Stage4 没有通过安全门：failed/interrupted 9 超过上限 4；同时 public-web 少 1、connector
少 1，未通过相应能力门。按预注册规则，Stage5 parent 回退到 Stage1，不能从 Stage4 续训。

Stage4 的有效结论是：平衡 ordinary-web/local-first hard negatives 将 Stage3 的 local network FP
从 0.30 恢复为 0，并把 mixed 从 2/20 提升到 17/20、privacy 从 2/10 提升到 9/10。Stage5
保留这一配对结构，但减少普通 local selector 重复，增加以下两类残差：

1. connector/web counterfactual，尤其 exact GitHub repository/file/commit 与普通官网、URL、文档页；
2. 工具成功后的 completion selector，覆盖 file_digest、read/list、calculator、local command、
   bind_evidence 和 privacy gate rejection，直接纠正 9 个 interrupted 族。
