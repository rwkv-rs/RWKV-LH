# Stage6 自适应配额登记（评价口径不变）

日期：2026-08-27；在 Stage5 冻结评价完成后、Stage6 数据生成前登记。

## Parent 与残差

Stage5 未通过预注册安全门，因此 Stage6 parent 按原协议回退到 Stage1 step500，SHA-256
`180fb98e70144d2d078bc3f9c43778c0d7011627c6b5446cfa7783041afd04f8`。

Stage5 的两个主要残差为：

1. 240 条完成后停止样本使 failed/interrupted 从 9 降到 1，但导致 mixed/privacy/local 的
   pre-evidence selector 过早选择下游动作或 `final_answer`；
2. public-web 21/25、connector 12/20，ordinary web 与 structured connector 的边界仍不完整。

## 固定数据配额

训练 1300 条：

- Stage1 完整 selector replay 500；
- Stage4 全部新边界锚 640：connector 80、ordinary web 160、local-only 160、mixed
  local-first 160、privacy local-first 80；
- Stage5 focused connector 残差 40；
- 新 ordinary-web residual 40；
- 从 Stage5 240 条 post-observation completion 中等距选取 80。

自身 dev240 使用与训练语义族隔离的新实例：connector 48、ordinary web 48、local-only 32、
mixed local-first 48、privacy local-first 24、post-observation completion 40。

所有新增 selector 必须通过真实 Controller 回放；不得写入冻结 ECRA 原题。exact overlap、
UTF-8 byte 5-gram cosine、远端 tokenizer/BOS/target suffix 契约维持总预注册门槛。

## 固定训练点

GPU0、FLA、bf16、ctx2496、BOS0、target_suffix、shuffle、1 epoch；seed832；LR
`5e-6 -> 1e-6` cosine；warmup40；只评价 final step1300，保存点 325/650/975/1300。

安全门、能力门、ECRA120 B、Round1 dev200、相似度算法和最终字典序选择规则均不修改。
