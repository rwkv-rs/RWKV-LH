# 工程优先整改 RWKV_ENGINEERING_FIXES_R1_20260914

## 任务级结果

Owner要求先解决工程问题再看真实trace。本轮整改阶段没有新增RWKV或强模型调用，没有重新评分历史任务；Agent Strict、真实合格任务率、真实mutation数不适用。受控客户端与本地子进程测试只证明工程行为，不代表RWKV能力提升。

上一审计阶段的62个目录/31个可重放运行结果保留在RWKV_ENGINEERING_AUDIT_R1_20260914；收到工程优先指令后未继续扩大真实trace分析。1万条数据仍为计划，未新建dataset或训练，未push。

## 修复、依据和验证

|问题|整改|回归证据|
|---|---|---|
|Goal无变化重复写入强制Final|Goal生命周期不再进入幂等重复强制Final；旧研究模式不改写。原观察、调用预算和原始回答规则保留。|RED_CORE：两次无变化写入后真实修改被挡；新回归修复后继续合法修改、零协议拒绝。|
|trace_complete仅检查写盘|共享生成配对审计，区分trace_persistence_ok与trace_complete，记录返回数和未闭合request_id。配对不是native tensor验证。|受控ConnectionError：请求开始1、返回0；现在不再报完整trace。|
|续跑只相信父RESULT标志|load_parent检查真实当前trace的请求配对和计数，不仅信任旧true标记。|RED_PARENT删除父返回事件后原实现仍放行，新实现拒绝。|
|旧只读续跑先建议后补观察|read_only与assisted共用append_pending_observations；待消费真实观察先于建议续接。|RED_OBSERVATION_ORDER原顺序为建议0、观察1；修复后观察在先。已完成父答案的正常续跑不变。|
|准备时间不计预算|编码、整目标、协助与依赖执行包裹同一协作式deadline；内层timer取更短剩余额度，不延长父预算。|RED_BUDGET_POOL：慢复制跨预算仍启动模型；修复后准备阶段中断、0模型调用、无交付。超时后的文件清单不能假装完整。|
|协助worker取消留下后代风险|独立进程组，timeout/BaseException清理进程组再回收。|本地真实子进程超时，后代未能写入延迟marker。此新增生命周期测试的首次red为缺失helper，不把它说成已复现所有历史孤儿进程。|
|进程池异常丢整批|逐future保留成功与失败，进程池创建/提交/返回失败生成逐任务结果；BATCH_ERROR持久化，未知调用数null。失败Goal归属unknown，避免误算RWKV独立。|受控BrokenProcessPool保留另一个原回答、失败记录调用数未知；RED_BATCH_PERSISTENCE确保落盘。没有杀真实模型worker。|
|只读调用重复复制整工作区|保存call与真实观察，省去只读工具before/after整树复制；修改操作仍保存快照。|新只读快照回归与原修改快照/真实观察回归。未声称实测成本收益。|
|依赖与集成缺口|同一CLI的depends_on声明；共享预检查、拓扑就绪执行、失败依赖阻塞；单父真实副本传递、多父同基线不冲突文件变化集成。|11项集成回归：独立变更、同文件冲突、删除/修改冲突、基线不符、篡改、路径重叠、环、失败依赖、串联、多分支汇合及CLI。|

新增回归最终在tests/test_direct_engineering_boundaries.py和tests/test_agent_integration.py。早期red日志中的tests/test_engineering_boundaries.py是开发时临时使用的同名路径；原有该文件已完整恢复且未修改，最终完整回归包含原有测试和新增测试，没有删测试换绿。

## 工程边界与尚未完成

- 调度器不拆业务任务；只有调用方明确声明的coding任务依赖进入新流程。独立任务照常RWKV优先，依赖流程不暗中增加strong角色。
- 依赖提交只证明存在可继续使用的交付材料，不代表满足需求；验证任务仍由模型选工具，最终外部验收保持not_evaluated，程序不改模型回答、不代写答案。
- 多父合并要求相同初始文件清单；一般语义冲突、不同基线重建、空目录和纯权限变化不在当前文件内容集成范围。发生不支持情况不宣称“通用合并完成”。修改内容时保留所选实际文件权限。
- 协作式signal deadline包含准备/执行；清理与审计落盘仍可能超时，并记录end_to_end_seconds/wall_allowance_exceeded。不是OS硬配额；不宣称任意挂死的内核IO也可即时回收。
- 编码纠正训练准入、统一费用和服务端峰值资源计账、前端续跑尚未完成。E03输入模板和E04历史重复策略仍是待对照问题，不凭本轮pytest判定它们解决，也不自动重置预算。
- 默认产品入口只用当前直接架构；旧研究角色内部依赖未物理删除。无故删除旧内部代码与owner未提交修改不属于本轮工程修复。

## 版本与证据

所有新增接口仍调用现有生产模型和输入构造函数。未修改rwkv_lh/model.py、supervisor_openai.py或owner两份测试。controller.py仅叠加Goal边界判断和恢复守卫，owner已有修改完整保留，并单独从提交中排除。SHA256.json包含源码、回归和过程文件身份；完整测试结果见FULL_TESTS.log。

## 最终验证

完整回归1671 passed、0 skipped，324.39秒；保留原有全部测试。新增19项边界/集成回归通过，受影响模块集中回归亦通过。详见FULL_TESTS.log及GREEN_*日志。没有使用角色通过率代替任务能力验收。

SHA256中的源码身份对应完整回归时的工作区（包括保留的owner修改），不是声称干净checkout单独验收；本轮提交的Controller源码另见STAGED_CONTROLLER_SHA256.json。原始日志及diff保留原空白，源码/文档git diff --check通过。
