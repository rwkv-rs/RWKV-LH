# R11 清理中止与原采集恢复

Owner 随后要求：会影响运行则先别删。立即停止后续删除。

- 已删除服务器 `/home/chase/eval-results/`、`/home/chase/chase/rwkv-skills/`；删除发生在最新停止指令之前。
- `/home/chase/GitHub/RWKV-LH-full-trace-runtime-r2-20260911/` 未删除，原 engine、State 与 journal 保留。
- 迁移候选 R11 engine 和 972 MiB journal 备份保留，候选 GPU 服务已停止；没有将其用于新采集。
- GPU 0 恢复 R7 原 launcher 与原 State，GPU 2 恢复 R10 原 launcher 与原 State。两端 capabilities 均恢复 native.17c34568eb664bf41887e22203151a08e0079139c7c78540adc661a7f1119609，与原冻结身份一致。
- 暂停前在途4题均完成并留痕后才停服务；队列对账284条 RL recorded（不是验收通过）。原 R10 campaign 已恢复，原预算/截止时间不变，第12批恢复时 recorded11/running4/pending17。未重跑已完成题。SFT/RL仍分开统计。
- GPU 1/3 未触碰；未训练、未纠错、未 push。生产代码未修改，沿用 R10 的1876全绿测试记录；本轮验证目录存在性、真实服务身份和队列实际续跑。
- 旧 selector 服务原已停止，本次取消其自启动；没有恢复旧 Selector。

证据：DRAIN_RECONCILED.json、RESTORED_CAPABILITIES.json、RESUMED_QUEUE.json、TWO_DIRECTORIES_DELETED.txt。迁移清单只代表已撤回候选，不代表当前服务身份。
