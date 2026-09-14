# Session采样配置传递修复 R1

任务级：没有新增任务通过率。触发对照R1已标INVALID；声明频率惩罚0.2但真实生成0.0，原始失败与中断完整保留。不能宣称重复惩罚无效或有效。

根因：LongHorizonModel在四个生成位置使用固定_SAMPLING，覆盖实际Session的RuntimeSettings；两种Session的未显式sampling分支又自行构造0.05默认。影响温度/top-p/top-k/presence/frequency/decay，包含直接动作、渐进选工具及保留研究的finalizer/auditor路径。基准metadata也引用此私有固定常量。

整改：SessionSampling.from_settings统一读取所属Session配置，prompt-replay/native两传输缺省使用它，显式sampling继续优先。四个上层调用不再覆盖；动作与选择的TempDecision从实际candidate.sampling记录。基准元数据使用执行Session默认配置，不冒称所有角色同值。未改唯一输入、工具参数、原始输出、State父链或业务选择。

兼容边界：产品默认仍0.1/1/0/0/0/0.996；过去直接Session.generate省略sampling时意外使用0.05，现在按RuntimeSettings（缺省0.1）。历史trace保留自身实际值，离线重放的显式sampling继续原样生效；不能重算旧结果为收益。各角色有自有settings时现在正确生效，需要按实际值重新冻结后续对比。

验证：生产直接与渐进调用、两种传输的请求/候选/trace均核对六个非默认参数；原4失败2显式覆盖通过，修后全通过。metadata边界另留红日志。124项针对性通过，完整1781 passed、0 skipped（见FULL_GREEN.log），包含Torch/State和浏览器。原owner五处修改保留，model.py仅本轮补丁入index。

后续：新实验worker在每次生成开始前校对登记与实际sampling，不符即拒绝继续；这只检查工程身份，不替模型选择动作。先进行已有代码单缺陷修复，再以R2两臂重新比较频率惩罚，不自动调整生产默认、不push。
