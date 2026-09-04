# S54 Selector state-tuning 上下文长度修订

登记时间：2026-08-29（Asia/Shanghai），在 S54 数据生成和训练之前。

S53 数据生成后、尚未生成 S54 时，使用项目 RWKV tokenizer 对全部 1,950 个冻结 V4 prompt
做了长度审计：最短 910 tokens，最长 2,381 tokens，773 条超过原预注册的 1,537 token 容量，
0 条超过 2,497 token 容量。长链后部正是本轮要训练的对象；使用 1,536 context 会机械截断
当前问题或历史步骤，违反 request-last 输入不变量。

因此 S54 的唯一修订是把 `ctx_len` 从 1,536 改为 2,496。数据条数、25 类 80/20 平衡、
seed 1054、exact-zero parent、2,000 steps、保存点、target-suffix mask、物理 GPU0、评价门槛和
全部禁止项均不变。最长完整 prompt + target 必须不超过 2,497 tokens，任何截断均 fail closed。
