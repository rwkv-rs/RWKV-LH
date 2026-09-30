# 第一轮：当前能力、工具整改与模型对照准备

当前实验入口为 `data/experiments/ROUND_01/`。只在本页维护当前状态；原始输入输出、失败、State/回执、产物、逐轮过程和SHA保留本地，历史查Git。

## Agent结果

| 批次 | Strict | completed | mutation | 独立整体验收 | 预算与用途 |
|---|---:|---:|---:|---:|---|
| 原十二道完整项目 | 0/12 | 0/12 | 55 | 0/12 | 每题64调用/1200秒；当前基线 |
| 新增108相关变种 | 0/108 | 0/108 | 122 | 0/108 | 每题32调用/900秒；十二题型各九变种 |
| 工具整改后六题 | 0/6 | 0/6 | 1 | 0/6 | 每题32调用/900秒；固定六方向工程验证 |

原120题已全部结束并完成逐调用审计。六题整改验证使用原变种V01的debug、环境、CLI、数据、Web、全栈，六题并发、各一次zero。终止为 `{"resource_budget_exhausted": 6}`。这些是有目的的工程验证，未做同代码两模型或旧/新随机对照，也没有两遍zero噪声参照；不据此宣称120题整体能力提升。原成绩未重算，失败未重跑，产物未人工补写。

当前仍不能把“能生成代码”当作“稳定完成项目”。保留的静态作品集样本可在桌面/手机运行，独立检查18/19，缺项是README；但120题中大量任务没有完成入口、启动或业务实现，并非普遍只差文档。mutation是工作区提交数，也包含命令产生的数据变化，不是修复成功次数。纯Web和全栈验收要求实际Chromium；服务无法启动时不声称浏览器业务通过。

新六题192次调用均返回并提交、无协议拒绝，但有73次工具失败：54次把OP回执ID当搜索分页游标，19次将`<`放入argv。debug随后7次只打印常量，未调用实际程序；唯一代码修改仍接受公开要求禁止的bool数量，其余五题没有修改产物。180对相邻Executor输入都送达上一条真实回执，82次原样重复的完整输入也都发生了变化。首错、原文和产物差距见`TOOL_CONTRACT_VALIDATION/DEEP_TRACE_REVIEW.zh-CN.md`。当前结果不支持完整交付已改善的说法。

报告：`PROJECT_12/REPORT.zh-CN.md` SHA-256 `da689b8c531b2d846466af70c549550299137a5d9dd04eef2e241530a23c9a0d`；`EXPANDED_PROJECTS/REPORT.zh-CN.md` SHA-256 `9af21aea2a2327ac4ba4860b1cac51a04dbd864680f71f6ec496048c5d725c83`；`TOOL_CONTRACT_VALIDATION/REPORT.zh-CN.md` SHA-256 `369473315961e08782140eb097e839911d4535c280dc1d75a3095d0f91e5be43`。

## 失败主要发生在哪里

120题已能直接进入Executor；新增108题有105个首个Decision为delegate，另外3题在首次生成前发生启动失败。只有1个新增任务在提交工作后进入强检查编写/审查，不能再笼统归因为Planner挡住开工。

主要缺陷是错误引用后重复、偏离用户公开接口、没有实际运行就报告、重复长正文或工具循环、以及检查绑定后没有推进验证。132次保留开发运行（120题加12次前端样本）的1,821次语义拒绝中，1,797次来自Executor、24次来自Planner、Decision为0；其中Executor的request_info为1,747次、report_work为50次，均是引用拒绝。类别可重叠，不作为互斥根因占比。120题中2,395次相邻原样输出重复的前后实际完整输入token均不同；预算/反馈已更新不代表模型已理解。

debug涉及错误回执和SHA，API涉及接口改写与遗漏导入，CLI/数据涉及根入口、JSONL/数值边界和持久化，全栈涉及用stdin程序代替HTTP服务，Web涉及长代码重复后截断。强服务也出现过嵌套参数缺失和无效JSON；运行器的已预留未发出、已返回未提交、仅服务端完成均独立记录。具体首错、前后调用与产物见错误目录和各批逐调用索引。

## 已应用的工具与职责整改

- 编辑SHA在共享schema中统一为64位小写十六进制，路径基本形状在同一注册处声明，生产输出校验、实际工具及decoder共用约束。
- 证据source是标签或URL，空标签可回退到来源路径；copy/move的source仍是受权限限制的工作区路径。
- 确定发生在工具预留前的校验错误返回模型反馈；已预留后的未知操作继续保留pending，不自动重发。
- Native只读能力探测和Planner实际共享请求预算检查前置；工厂复用能力响应并保留底层诊断。State创建已发送却无明确登记等问题仍单独保守处理。
- Decision选择方向并根据验证判断目标，Executor连续读/改/运行/修错，Planner按需设计、诊断及独立审查。完整用户义务、权限、真实回执、State身份和完成门保留，Controller不代选动作。

工具名、参数名和必填字段不变。职责文字减少：Decision335→242、Executor425→269、Planner计划768→448 token；补齐参数约束后，Executor工具定义加职责合计3214→3307，因此不宣称所有输入变短。详情及当前定义对比见 `TOOL_CONTRACT_CLEANUP/IMPLEMENTATION_DESIGN.zh-CN.md` 和 `CURRENT_TOOL_SURFACE_COMPARISON.json`。

同66个有限工程边界探针中，schema放行而normalize拒绝从49降至0；181个实际Guidance/RWKV tokenizer离线探针通过。真实六题已提交调用的合同异常数为0，各修复路径是否实际触发见 `TOOL_CONTRACT_VALIDATION/ENGINEERING_PATH_COVERAGE.json`，未触发项明确登记。形状正确不证明引用、权限或业务内容正确，单测通过不替代Agent验收。

## 调用、证据与数据入口

六题预留192次、开始192次、客户端返回192次、提交边界192次；已提交角色为 `{"decision": 6, "executor": 186}`。已提交Native 192次/11461 token，客户端返回但未提交0次/0 token，仅服务端完成0次/0 token，分别对账。Strong原始tool_calls/SSE、原始/消费token、父State、逐步工作区及最终只读快照均留证。未提交输出不回放成动作。

`TASK_INVENTORY_120.zh-CN.md`和`EVALUATION_120.zh-CN.md`列出120题；各批`CALL_INDEX.zh-CN.md`定位原样输入输出。`ERROR_CATALOG/`仍以原132次保留运行作为独立基线目录，新六题的诊断与产物对照放`TOOL_CONTRACT_VALIDATION/`，不混合不同预算的成绩。

`ERROR_CATALOG/ALL_CALLS.jsonl`包含3,476次已知客户端返回；`OCCURRENCES.jsonl`保存7,550个可重叠观测事件，`DEFECT_CARDS.json`整理27类已核实缺陷，`ARTIFACT_REVIEWS.json`对照真实文件、语法、入口和执行回执。`SEMANTIC_REJECTION_BREAKDOWN.json`按真实角色及原始动作拆分，`REPEAT_INPUT_AUDIT.json`核对重复前后的实际输入，`DATA_DESIGN.zh-CN.md`说明纠正方向与来源隔离。

这些是开发评测材料，正式角色训练行0、训练步骤0。私有验收/reference/mutant不进入Agent工作区或训练标签；不能把评测答案或脚本化单测当作生产角色来源。后续角色数据仍须从真实生产trace提取并独立审查，工程异常先修工程。

下一阶段优先复查搜索游标的共享形状合同，保留运行时对真实来源和查询绑定的检查；不能将错误ID自动改为游标。能力方向重点是从定位转到读写验证、失败后实质改变动作、真实运行程序而非打印常量。修复分支在六题中未实际触发的项目明确标记未覆盖，避免将单测或角色格式通过冒充Agent收益。

## G1k后续任务

已登记独立持久任务 `G1K_FOLLOWUP/TASK.json`。当前工具没有新建Codex侧边栏任务接口，未声称已创建侧边栏任务。

[官方G1k13.3B权重](https://huggingface.co/BlinkDL/rwkv7-g1/blob/main/rwkv7-g1k-13.3b-20260930-ctx25600.pth)已完整下载到本地，并与NAS核对完整SHA。固定revision `cd67fb95fa9e2ce8757f8d21d713e74a9c788118`，26,540,868,485字节，SHA-256 `31799b3f8207e74c1b47f359184ac1c658c927ff697971447f7bf0fd18ae393f`。NAS原本已有正确文件，核验后复用，未重复上传。回执见 `TRANSFER_COMPLETE.json`。

本地已使用冻结engine完成转换：61层、4096隐藏维、65536词表，原始2019个tensor中2016个映射tensor逐项验证dtype/shape/value一致，3个未使用的首层value-mix参数另存。证据见`WEIGHT_LAYOUT.json`和`CONVERSION_COMPLETE.json`。尚未加载G1k到GPU，也未开始能力对照；同形状不表示旧State可以复用。

后续分开测试相同24576预算下的模型差异、预登记提示词/输出外壳的格式差异，以及G1k完整25600上下文的额外收益。共用唯一角色协议和语义合同，保留原始请求、代码和回执，不能无差别压缩事实字段的空白。官方当前模板适用于G1系列，不足以证明G1k特有偏好。

整轮对照先解决资源预算：六题运行前服务器约126GiB空闲；已保留108题工件约261GiB，按此粗估两模型各120题需新增约579GiB，双重复约1.13TiB。具体以`CAPACITY_ASSESSMENT.json`及开跑时核验为准。不能为腾空间删除待复核证据或把State放进只存原始权重的NAS目录。

## 架构、回归与发布

完整目标→Decision基于证据选择直接执行或强规划→Executor持续执行与局部修正→独立检查→Decision判断目标满足→完成门。当前唯一协议为Ledger v10、Goal v1、Plan v5、Assignment v6、Planner v14/chat v3、Decision v17、Executor v13；prompt v7、输入传输v2、格式适配v6。细节只在[架构](ARCHITECTURE.zh-CN.md)维护。约束解码保持默认，新实验全部启用。

完整本地回归 **3043通过、0跳过，729.94秒**，全部源码/脚本/测试文件集合及SHA在运行前后相同。Torch、State及必需浏览器检查未跳过。初次26失败/12夹具错误及修正过程在`TOOL_CONTRACT_CLEANUP/FULL_REGRESSION_ATTEMPT_01.*`和`FULL_REGRESSION_REPAIRS.json`保留；旧trace不改写，当前生产重放仍拒绝旧工具菜单。正向机制测试使用明确的脚本化传输，不能作为模型能力或训练证据。

owner既有未提交研发改动保留。完整工作树回归和六题运行包含这些改动；公开提交只包含本次维护源码、架构文档和必要构建配置，公开源码的构建/入口CI不替代完整本地回归，也不冒称与整个研发工作树相同。公开分支为 `chase/g1j-agent-improvement-public`，边界见[发布规范](SOURCE_DISTRIBUTION.zh-CN.md)。实验、测试、trace和生成产物只保留本地。

当前120题及六题服务/隧道均已停止，证据保留。没有操作远端Git、Holdout、OA、正式训练或新datasets版本。G1j本阶段工程整理和验证已完成；模型重复、引用与完整交付能力仍需后续对照和合格生产数据改善。
