# RWKV-E2E-90 v1

这是 Round1～Round10 使用的固定 90 题数据集登记。题目分为 Basic、Medium、Hard 三组，
每组 30 题。可见题面保存在 benchmarks/rwkv_e2e 下三个版本化 catalog；本目录通过
manifest 固定其来源和 SHA-256。

codex_reference_answers.json 是在任何 RWKV-E2E-90 实验输出产生前冻结的 Codex 参考解答。
每题包含人工解答摘要以及机器可比对的隐藏 observable 来源。运行时禁止把本目录、acceptance、
解答摘要或其派生内容加入 RWKV 输入。

诚实性说明：原有 42 题的 acceptance 在本次会话开始前已存在，且审计时被检查过，因此不能
声称这 42 题是严格的盲答；Codex 仍逐题重新给出了解答摘要。新增 48 题及其参考结果是在任何
RWKV 模型运行前创建和冻结。无论哪一组，参考结果都不会进入模型运行路径。
