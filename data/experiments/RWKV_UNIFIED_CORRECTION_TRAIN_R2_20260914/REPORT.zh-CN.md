# RWKV_UNIFIED_CORRECTION_TRAIN_R2_20260914

任务级：本轮新Agent验收未运行；没有新Strict、completed、mutation或任务通过率。训练在验收前失败，NO_KEEP，不把83步或loss当作Code Agent能力。confirmation/holdout未运行，默认State未替换。

训练级：57行（28读取、24回答、3编辑、2命令），zero初始化、lr1e-4，计划6epochs/342步；实际83 optimizer steps、84样本进入前反向、完成1epoch。第84样本反向后触发“State gradient is missing or nonfinite”，第84次更新未执行。原报告optimizer_step_in_flight为null，未导出候选。失败历史保留，不用replacement清零。

耗时1097.695秒（含身份核验和加载）；峰值69.483GiB，低于80GiB预算。因此本次不是已证实的显存预算中断。

失败样本按注册seed重建顺序，并用每步累计target tokens核验：index_code_first-v3，5499输入/437目标token，来自原有回答样本，不是新增24455-token最长样本。首遍经过此样本，第二遍失败。原日志没有记录具体层或区分None/NaN/Inf，不能先断言根因或将其归为RWKV任务能力问题。原结果loss字段是最后成功步，不是失败样本loss。

复现下一步：冻结独立诊断run，重复相同数据/seed/优化路径，最多84实际步并单独计账；在83步后封存精确FP32 State及梯度hook。若复现，在同一State/输入上仅做预注册loss scale=1、1/8、1/64、1/512的反向探针，不更新参数；检查缺失/非有限梯度、层、范数及下溢/差异，不预设缩放就是修复。当前未对生产训练代码实施数值修补。

数据manifest 2c8191f9774d2e5e4ac572b5d71dd58245ae71bb5a90244b25c5c14e4b6fa36d；训练注册787692fdeb80b7b3affd967e651e81048763e302a41034b4f7a52f693eb63f78。训练数值模块及model_io与已验证R1字节相同；新生成快照准入走当前freeze，并重新真实执行验证。实际输入/纠正/State绑定在PREPARATION和前轮纠正原始证据中。

训练启动SSH引号错误0步、服务恢复就绪等待原样保留。原服务已由ExecStopPost恢复并核验active，随后只为已登记GPU0数值复现再次暂停；复现单元也有自动恢复。GC侧transient服务仍暂停，须按原launch重建。服务器未运行Git，无push。

已准备的原固定zero/candidate评测脚本未执行，不改原口径；57行v2不可变。完整生产1758回归是训练前源码证据；后续E12交付状态整改另轮记录，不混入R2两臂成绩。
