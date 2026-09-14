# 重复惩罚对照 R1：INVALID

本轮不提供有效任务对照结论、不作为训练收益。已结束四个任务均预算终止，无合格交付；另两条执行在发现配置错误后中断，最后一组未运行。

登记frequency_penalty=0.2，但所有已保存真实生成sampling仍为0.0。根因是生产LongHorizonModel._SAMPLING硬编码覆盖Session配置；Session本身不传显式sampling时也忽略RuntimeSettings。已停止本轮独立服务及两个本轮worker，原服务恢复。中断时未返回的生成保留，不补写结果。

完整声明、实际输入输出、State、快照及失败封存。后续修复参数流后以R2两臂重新冻结运行，不将这些运行改名为新基线。

生成开始数：{"repeat-1-frequency-0.0": 16, "repeat-1-frequency-0.2": 16, "repeat-2-frequency-0.2": 8}
