# 执行修复复测、waiver复核与架构评估

日期：2026-09-10。客户端冻结提交b3e89de6。**Agent Strict 0/15、completed 0/15、mutation 4、动作28；5题无进展、3题协议拒绝、7题Planner余额不足中断。KEEP未成立。**

## 固定15题复测

| 题集 | Strict | completed | mutation | 动作 | 终止 |
| --- | ---: | ---: | ---: | ---: | --- |
| UltraData固定3题 | 0/3 | 0/3 | 4 | 5 | 协议拒绝2、无进展1 |
| 项目开发固定12题 | 0/12 | 0/12 | 0 | 23 | 无进展4、协议拒绝1、Planner HTTP402共7 |

全部15题运行器均输出结果并保留原分母，不代表Agent完成。UltraData耗时635.47秒，项目集1008.93秒；每题1800秒、每组原总预算、200 transitions、zero State、官方DeepSeek low thinking与原评分保持登记值。Native客户端最多2次POST尝试，benchmark显式native_transport_resume_attempts=1。特别注意旧采集驱动直接调用run_case，其函数默认仍为0；新驱动显式传1，没有只依赖CLI默认值。

7题未进入RWKV：RP-CLI-02、RP-DATA-01/02、RP-FULL-01/02、RP-WEB-01/02。官方原文为HTTP402 / Insufficient Balance，响应摘要SHA a00c4a12749ac4093ce2cc2bd5914a413415fb76107f9d4c4644b19bf63a123a。原失败事件保留；没有换供应商、改预算、补跑旧结果或重评分。Owner随后已明确充值完成并授权继续；7题在独立R2登记重跑，本R1结果保持封存，不能声称本R1已完成这7题的模型能力复测。

本轮没有Native传输错误或Supervisor输出耗尽，包括每次重试前响应。最新15题基线本就无输出耗尽，0→0不是严格下降；旧RP-CLI-02事故及RP-WEB-02执行路径本轮均未到达，不能用“未出现报错”宣称对应修复通过实题验证。Strict0→0也不构成能力改善或完整KEEP证据。

12题原隔离黑盒验证器均实际调用，workspace为只读snapshot、network/pid独立且不挂仓库。4道Web/全栈按browser要求调用既有验证流程，exit code均1，2道Web有Playwright诊断；全栈未进入可用应用，不能宣称浏览器行为通过。只读取执行元数据，没有读取私有程序/期望值或Holdout，没有把其反馈传给Agent。

## 角色与交接

47个Selector选择边界；Executor74次、Step Auditor26次；100/100已返回生成完整token及100/100角色输入字节重建通过。Finalizer/Final Auditor为0，7个余额不足来源无生成；0/0不算验证通过。角色语义错误、格式拒绝和重复动作仍存在，详见ARCHITECTURE_FIT_REVIEW.zh-CN.md。实际optimizer steps 0，未创建正式数据集版本。

## waiver：保住原9边界，拒绝无条件全量等价

按owner本轮明确授权，两个独立AI reviewer完成六文件SHA diff与实际15来源审计。原全量draft未获一致批准，保持原样；check_command语义和工具描述确实变化，不能把字节一致当执行标签等价。

另立具体14来源、仅Selector的scope，排除受旧Python/ELF执行缺陷影响的RP-WEB-02全部21行；两人对注册、waiver与强制作用域wrapper的精确SHA共同accept。正式生产CLI重提取成功恢复14来源：60自动候选（55/3/2）、126待复核。候选INVALID，execute覆盖0，281对跨切分比较中101对超原0.95阈值；exit2属于质量门失败，不是来源SHA准入失败。

原复核包9边界/27行在新review_queue中全部保留：完整原始行、输入SHA、协议source、request id、原输出SHA与证据引用一致。既有复核劳动未丢失；approved_labels仍0，waiver技术复核不冒充语义标签批准。详见WAIVER_RESULT.md和LEGACY_REVIEW_PRESERVATION.json。

## 环境、测试与可复核记录

实际WSL UbuntuRecovered；uv冻结环境和Chromium安装均完成。本地29613/29621原无监听，恢复SSH转发后两项服务health/identity通过。服务器完整源码按上传manifest验证：project 0953f64292f0a0411ca42f9b8b5f7452af5cec11b8b3f12c90c5976a927434e0；engine 07bb8f39eba57b513e862bf23dd439e11cd264a03ce1c942678d140466c2b352；Native identity 4970b89a548fc5b1dffbbdff91c3be2021f3cd953c934d343458b576e48b5c35。服务继续使用其已验证上传版本，客户端使用新冻结版本，未在服务器调用Git。

首次全测2 failed/1445 passed，两个独立reviewer同时使用pytest默认basetemp清理了同一目录，失败均为SQLite unable to open database file；这是本轮测试编排干扰，原日志保留。全部reviewer停止测试后串行完整重跑：**1447 passed，0 failed，无skipped，244.64秒**。测试后生产源码未变；本轮仅增加分析、评测与复核工件及交接文档。未改rwkv_lh、评分、parser、stop boundary或旧实验。

主证据：AGENT_SUMMARY.json、ROLE_AND_INFRASTRUCTURE_EVIDENCE.json、REGISTRATION.json、PYTEST.log、PYTEST_ISOLATED.log、UPLOADED_SOURCE_VERIFICATION.log、SCOPED_APPROVAL_ONE/TWO.json、SCOPED_EXTRACTION_COMMAND.json。完整路径、bytes与SHA-256见EVIDENCE_SHA256.json；摘要本地提交，owner负责push。
