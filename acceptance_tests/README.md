# 最终验收专用测试

本目录不在默认 pytest testpaths 中。这里的测试会读取 Real Agent Holdout V2 的题目和隐藏验收，只有最终一次验收时才能执行；普通开发、协议整改和全套单元回归都不得执行本目录。

冻结题集仍位于 `benchmarks/rwkv_e2e/rwkv_real_agent_holdout_v2/`，冻结登记与来源材料保存在 `data/acceptance/`。本轮仅迁移目录位置，没有读取或改写这些冻结文件。

旧合成训练数据已按 owner 要求删除。冻结相似度审计引用的旧 source registry SHA，与本轮删除前登记的 SHA 比较；不恢复旧数据、重新运行相似度审计或修改冻结分数。该一致性检查不等于重新计算相似度。
