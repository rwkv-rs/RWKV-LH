# RWKV_ASSISTED_AGENT_R1_20260914

## 任务级结果

固定接口smoke **2/2满足事前登记目标，2 submitted、mutation 0、协议拒绝0**。其中RWKV独立完成0项、强模型建议后完成1项、强模型接管完成1项、未完成0项。不是项目Strict，也不是修复成功率提升：两项父任务此前已经成功，本轮只验证显式协助接口。

- advice-health：原目标不变，强模型生成一次建议，RWKV沿原State输出健康检查摘要；涵盖GET /health、状态200、ok=true，明确不验证预订/订单，没有虚构实际运行。
- takeover-recursive：强模型从新文本根接管，自主重新执行python check_recursive.py；真实exit0、passed=true，两项checks为true，最终回答忠实引用，文件未改变。父轮同名执行属于历史，未当作本轮新执行计数。

外部审核按REGISTRATION.json登记的任务主旨和事实忠实性进行，不要求逐字匹配；两项原回答见live/*/DELIVERY.json，实际工具输出及State见各execution目录。直接读取原结果进行人工审核，不把submitted自动换算成通过。

## 模型和资源诊断

新增RWKV生成1次，精确逻辑输入2835、输出195 token；新增强模型请求3次（建议1，接管2），提供方usage合计输入11958、输出1063 token，其中包含reasoning token，不伪称有强模型逐token ID。父任务调用不重复计入本轮新增调用，但完整项目成本须连同父任务、失败及重试一起计算。

执行计时分别37.920s和4.430s；不是包含建议、排队、复制的端到端耗时。未测峰值资源、实际账单或吞吐收益。本轮强模型实际为deepseek-flash；原始请求中的thinking/reasoning选项见RESOURCE_DETAILS.json和provider trace。注册已冻结RWKV采样、源码、任务、预算；强提供方选项以原请求作实测记录，未逐项提前写入注册，不能用于宣称严格性能对照收益。

MECHANICAL.json核验native逻辑输入token重建、原父State连续、工具结果exact spans、强模型新文本根、实际system输入及原始输出一致性。父RESULT和State快照与复制件逐字节一致。建议是非执行证据；接管没有传递RWKV张量。原始最终文本未经Harness改写。

## 架构变化和依据

1. 新assisted_agent把显式advice/takeover接入已有agent_batch及CLI。复用生产Controller、ModelSession和唯一输入构造，不增加Planner或逐步审核。父目标/权限继承，输出和工作区独立；WSL mount namespace保持原目标路径含义。
2. 新strong_session仅承担强提供方传输和原始信封审计，原始非法回答仍交生产parser拒绝，不自动修复参数或答案。提供方错误保留已写trace并如实失败。
3. 修复新接口中的待消费观察交接：红测证明建议先于观察、接管重复投影风险；现在建议前追加缺失观察，接管用已有acknowledge_projected_event登记已投影观察。两模式红2失败→绿6通过。旧父事件不重复注入。
4. 删除旧多角色CLI、对应启动测试、runtime stack启动worker的选项，以及两份重复架构文档。删除路径/SHA见DELETED_FILES.json；历史从Git查询，不保留archive代码。仍被研究回归或共享执行依赖的内部模块保留，未动owner共享代码。

完整回归：1641 passed in 314.10s，零跳过（含Torch/State与浏览器测试）。初始接口红测及GREEN.log、边界PENDING_RED/PENDING_GREEN、完整FULL_TESTS.log保留。源码冻结REGISTRATION.json逐文件SHA；owner五处改动与OWNER_BEFORE.diff核对一致，不混入代码提交。

## 能力边界和下一步

本轮交付显式协助框架，未证明自动困难识别、多文件自主修复、共享文件合并或协助能恢复全部失败。旧研究内部模块仍有测试依赖；没有为清理而删除共享执行能力。工作区副本是隔离交付，不是完整安全沙箱。未运行训练、未建dataset、未做前端、未push。

下一步优先在已有真实失败任务上冻结有限建议/接管预算，测恢复质量和总成本；然后增加显式依赖与集成任务，验证冲突和最终交付。不再为每个局部错误增加角色或训练一轮StateTune。现存失败、建议与接管成果分别归因，不能自动转成RWKV独立训练标签。
