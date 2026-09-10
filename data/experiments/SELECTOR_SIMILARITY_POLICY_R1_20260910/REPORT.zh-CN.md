# Selector相似度策略 R1

本数据轮无新Agent分数；关联四题为Strict 0/4、completed 0/4、mutation 0，三题无进展、一题协议拒绝。去重合格不代表Agent能力改善。

运行前预注册保留原始project-family哈希切分、完整UTF-8 byte5gram count cosine、阈值>=0.95，精确整数比较；以真实selection boundary及其菜单行为单位建连通分量。涉及原5条开发/确认anchor的分量剔除全部train；纯train分量仅保留(source_run_id,run_id,boundary_event_id)字典序最小单元。没有更改输入、阈值、family、评分或把train移入验证集。

原60自动候选按该规则保留14（9/3/2），原101/281跨切分超相似对清零。加入102双审标签后162→20；新采集14自动加入后176→20；再加入新34双审后最终210→20，训练/开发/确认=15/3/2，7分量，190行按完整身份排除，原5anchor全字段不变，最终跨切分超相似对=0。所有中间结果均保留，不因最终覆盖不足更换代表行。

最终required flags：mutate9、py_root9、missing_target6、execute0。非空切分与相似度门通过，required coverage失败，候选仍INVALID。没有发布虚假的regression fingerprint或正式角色数据集；也未把33条语义reject算作未复核。原始审阅共169条均已处置，136共同接受（52原标签+84纠正）、33剔除。完整排除原因见final210.EXCLUSIONS.json。

当前冻结入口未支持waiver与此已注册筛选规则的再现，需单独接线修复而不能跳过重提取；细节见SELECTOR_TRAINING_PREFLIGHT_R1_20260910。optimizer steps=0。
