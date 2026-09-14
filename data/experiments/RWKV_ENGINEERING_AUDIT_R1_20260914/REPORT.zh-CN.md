# 工程审计 RWKV_ENGINEERING_AUDIT_R1_20260914

结论：工程问题没有全部解决。本轮只审计，不修改生产实现，不启动模型服务、训练、新数据集或push。任务级Strict/合格完成/mutation不适用；没有新增真实模型任务，历史验收不重算。受控客户端探针不是RWKV能力实验。

## 范围和证据规模

静态检查当前batch、goal、coding、read_only、assisted、strong_session、controller/model终止边界、Harness命令入口、task_review与direct_trace_data；保留owner五处修改。完整tests回归另记，不能等同于生产全部场景覆盖。

按REPLAY_REGISTRATION.json事前列明7个近期实验目录，抽取存在RESULT、State快照和model_trace的62个运行目录，10种不同任务文本（不是10个独立问题家族）。31个运行、108次生成精确重放；其中files19、coding12，包含原生建议续跑。没有inspect通过样本，不声称覆盖全部工具scope。请求文本不同仍可能同一query问题，重复调用不算独立样本。

拒绝31：bootstrap不符20、observation不符6、模型身份不符4、缺失/重复生成身份1。详见REPLAY_COVERAGE.json，拒绝不是模型任务失败率。强模型接管不能按RWKV zero身份准入；历史构造不符不得通过兼容旧renderer放行。剩余拒绝需按原来源身份单列归因，不能本轮一概说旧版本，也不修改评分rescore。

## 已实现且有回归支撑

- 单文件路径约束、只读菜单及执行权限、真实工具观察和原回答交付；预算中断不等于验收通过。
- 正常native观察父链与建议前待消费观察处理；强接管创建文本根、不移植RWKV张量，投影观察避免重复。既有tests/test_assisted_agent.py和生产重放支持，但没有证明任何崩溃点都可靠。
- 独立任务spawn执行、输出与所有输入/输出的重叠预检查、修改副本；普通Exception隔离记录。
- 外部task_review区分met/partial/no_delivery/invalid等，要求源证据与合同身份；执行返回not_evaluated，非自动验收。
- E06 coding菜单重放修复扩大到12个coding运行通过；不代表编码纠正标签已经可训练。

## 仍未解决或仅有部分保证

|优先级/性质|证据与影响|建议最小验证/修复|
|---|---|---|
|P1 当前策略冲突|controller.py:459/479/716：幂等写入重复且无变化后生成forced_terminal_event，model.terminal_answer只开放final。现有回归甚至要求此行为。生产直接模式可触发，并非仅退役代码；不能称全自主终止。|先以两次无变化写入后模型选择合法验证/不同修改的回归证明被挡，再把停滞预算与强制Final分离；保留原实验的强制边界归属。|
|P1 审计字段语义不足|read_only_agent.py:286 trace_complete只检查audit_errors。受控客户端ConnectionError：generation_started=1、无返回、trace_complete=true、termination=error。当前错误仍被goal路由排除，未复现错误接管。|分别记录持久化成功、请求已闭合/失败、完整可重放性；无响应不应伪造token或成本。测试连接断开、超时、写盘失败和响应已到但提交失败。|
|P1 预算边界不统一|coding_agent在_run_job计时前copytree，之后还inventory；探针在复制插入0.15秒，0.05秒预算实际0.335秒。goal明确仅记录overrun；assisted父检查/建议/复制不在执行计时，外层timeout额外240秒。|明确整任务deadline，剩余额度传递，确保中断后的子进程清理与审计；禁止把现在的max_seconds说成硬端到端上限。|
|P1 并发故障覆盖缺口|agent_batch.py:89-90直接list(pool.map)，_worker只捕获普通Exception；子进程硬退出/BrokenProcessPool没有逐任务补全结果的路径。此项静态确认异常处理缺口，本轮未杀真实worker复现。|用受控worker硬退出验证其他完成结果保留、未完成标记与批次报告持久化，再补恢复；不自动重放有副作用任务。|
|P1 未实现|共享文件冲突、依赖调度、集成和最终验收未闭合；batch仅独立任务，不自动合并。|显式依赖和集成任务，覆盖同文件冲突、失败依赖、集成测试；不是StateTune能替代的工程。|
|P2 数据通道缺口|direct_trace_data可重放coding，但normalize_direct_row只支持已验证读取/独立摘要审查标签。|编码纠正候选在隔离源快照真实执行并按用户入口验证，审核当时可见证据，再准入。|
|P2 资源/性能未闭合|_RecordedHarness每次工具调用都复制完整before/after，即便只读。全项目放大IO和磁盘成本；delivery未统一汇总建议费用、峰值资源或物理增量token。|先量化快照占用/耗时；失败、重试、建议和接管统一计账。不可凭并发smoke声称便宜或更快。|
|P2 生命周期/隔离边界|复制目录和mount namespace不等于完整主机隔离；Harness命令默认请求bubblewrap，缺少时拒绝，不应误报成完全无沙箱。外部进程同时改源不在原子快照保证内。|检查活跃源快照一致性、后台进程与取消路径；明确支持环境。|
|P2 遗留结构|默认产品路由统一，但共享Controller仍含旧角色、原子合同及监督路径，仍有研究依赖。|按依赖和行为边界清理，不能直接删除owner未提交修改或把保留分支都说已经退役。|

## 与模型问题的边界

M10写回原代码、M11虚称改好有真实轨迹支持；但工程未全闭合，不能把其余停滞、截断或接管差异统一归给RWKV。E03模板、E04历史重复计数仍需对照，普通pytest不能证明没有输入敏感性。固定两条不够；扩大来源后仍不能把目录数当多样任务数或1万条训练准备完成。

## 建议顺序

先修自主终止与审计真实性，再统一deadline/并发故障报告；随后编码纠正准入与依赖集成分别推进。每项工程修复独立红绿，不因一次模型失败增加角色。本轮只形成证据与优先级，尚未将上述缺口标解决。

审计基线完整回归：1652通过，0跳过，313.14秒。随后owner要求工程优先，停止继续扩大真实trace检查；修复记录转到RWKV_ENGINEERING_FIXES_R1_20260914。
