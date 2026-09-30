# 第一轮：当前能力、120 题测试与缺陷积累

当前入口为 `data/experiments/ROUND_01/`。本页只保留当前能力和正在进行的工作；逐调用原文、实验材料、生成产物及 SHA 保留本地，历史只查 Git。

## 当前已完成结果

原 realprojectdevv1 十二道项目已全部结束：**Strict 0/12、completed 0/12、mutation 55、独立整体验收 0/12**。终止为输出预算耗尽7、操作状态不确定2、调用预算/时间预算/执行异常各1。每题一次，64次调用/1200秒；没有补写产物或重跑失败题。

12/12 首个 Decision 动作都是 delegate，没有前置强 Planner 阻挡开工。只有库存 API 和工单全栈在报告工作后进入强检查编写/审查。当前问题主要发生在 Executor 的目标对齐、引用准确性、连续实施和验证收尾，也包含检查与运行器缺陷。

| 方向 | 实际产物与失败位置 |
|---|---|
| 维护/debug | 一题把目标 ID 当回执，63次拒绝；另一题反复列目录、用错 SHA，124位 SHA 触发执行前异常；两题均未修改工作区 |
| HTTP API | 预约题改成 rooms 接口，原 bookings 入口未实现；库存题写出服务，但遗漏 argparse 导入，启动失败 |
| CLI | 备份代码写入子目录，缺固定根入口；工时账本做成计时函数，缺 timebook.py；报告引用失真或重复正文后中断 |
| 数据 | 对账程序在有效输入上触发 decimal.InvalidOperation；日志项目缺 accesslog.py，重复生成测试导入后截断 |
| 全栈 | 工单 server.py 有语法错误；投票项目只有子目录 README，服务器输出截断未落盘；均未完成可用服务 |
| Web | 看板在 JavaScript 未写完时截断；阅读清单在 CSS 重复时截断；均无页面文件 |

当前保留的静态作品集样本仍证明能生成基础展示页：桌面/手机可运行，独立检查18/19，唯一缺项为 README。这一结论不推广到其他任务；十二题失败并非普遍“只差文档”。

报告：`PROJECT_12/REPORT.zh-CN.md`，SHA-256 `da689b8c531b2d846466af70c549550299137a5d9dd04eef2e241530a23c9a0d`。`CALL_INDEX.zh-CN.md` 索引304次已提交边界原文，额外未提交返回单独保存。

## Trace 与验收可信度

共预留307次、开始305次、原始返回305次、已提交边界304次。已提交角色调用为 Decision14 / Executor244 / Planner46。两次 Planner 在预留后触发本地输入预算、没有发起生成；一次 Executor 原始返回存在但未提交，任务因时间预算结束，未执行其动作。

259次已知 Native 原始返回共98,718 token（含1次未提交返回的250 token），已与服务端 journal 独立核对，无仍未匹配生成。251次完整已提交 Native 参数通过共享 schema，7次截断不作为完整参数通过；112次是引用值语义拒绝。官方 Planner 46次请求、57个 tool_calls 中1个原始返回缺嵌套必填 cwd/purpose，解析器正确拒绝。格式/引用、原始返回/执行提交、模型声称/真实回执分别统计。

原十二份 reference 在同一隔离环境下预检通过，不计 Agent 成绩。产物通过只读 snapshot 独立验收；纯 Web 实际 Chromium，全栈在服务启动失败处已被拦截，未宣称浏览器业务流程通过。

## 已完成的 120 题基线

原十二题加新增108变种已全部结束、逐题独立验收并完成逐调用审计。新增批次：**Strict 0/108、completed 0/108、mutation 122、独立整体验收 0/108**。终止分布为 `{"resource_budget_exhausted": 59, "model_output_budget_exhausted": 11, "execution_error": 8, "uncertain_operation": 3, "wall_budget_exhausted": 27}`。全120题无完整通过；保留的十二次前端样本不占此分母。

新增十二个题型各九个公开边界样例变种：debug、环境/包入口、CLI、数据、纯前端、全栈各18题。变种相关性高，不视为108个独立业务。108参考实现全部通过、108故障对照全部被拒；私有验证和作者reference/mutant不进入Agent工作区。题面、验收和实现运行期间保持冻结，没有补写Agent产物或重跑失败题。

新增每题32调用/900秒、并发8；原十二题64调用/1200秒、并发2，分批报告，不据此归因性能提升。新增预留3016、开始2999、客户端返回2995、提交边界2986；已提交角色为 `{"decision": 107, "executor": 2858, "planner": 21}`。未提交返回与服务端journal单独对账，保留原pending及终止结果，不回放动作。

新增模型问题集中于错误引用后重复、修改公开接口、未实际运行便报告、重复长正文，以及检查绑定后不推进验证。Web和多数全栈题没有形成新功能产物，不能概括为只缺README；少数CLI/数据程序可运行某些输入，仍未满足完整边界。共享参数校验、初始化和强检查也存在独立工程问题。

服务端另有4次生成完成但无客户端返回，已补充原文与124个token审计，见`SERVER_ONLY_NATIVE_AUDIT.json` / `SERVER_ONLY_INDEX.zh-CN.md`；没有把这些输出提交为动作。120题范围内2,395次相邻原样输出重复的前后实际输入token均不同；预算/反馈更新存在不等于模型已理解，不简单归因为重复发送同一输入。

报告：`EXPANDED_PROJECTS/REPORT.zh-CN.md`，SHA-256 `9af21aea2a2327ac4ba4860b1cac51a04dbd864680f71f6ec496048c5d725c83`。全部题目见`TASK_INVENTORY_120.zh-CN.md`，全量原文见各批`CALL_INDEX.zh-CN.md`；当前汇总为`EVALUATION_120.zh-CN.md`。README弱检查、有限样例、首错即停和变种相关性等限制见`EXPANDED_PROJECTS/VERIFIER_COVERAGE_NOTES.zh-CN.md`，未在运行后改评分。

## 当前 goal 与后续模型任务

owner 已要求持续完成当前阶段，并清理工具描述与职责。当前 goal 包含120题完整审计、缺陷总结、工具/职责精简、已证实工程问题的回归修复和新受控运行验证。120题基线已完成；工具修复仍待应用并经过完整回归及新受控运行。`TOOL_CONTRACT_CLEANUP/BASELINE.json` 保存当前完整定义和规则，`PLAN.zh-CN.md` 说明必要语义与验证边界。

修复候选在独立临时目录离线验证，未进入这批模型运行。它统一路径/SHA参数约束、区分证据标签与文件路径、保留未知操作门，并前置预算和能力检查、精简角色说明；先失败回归和相关验证记录见 `TOOL_CONTRACT_CLEANUP/CANDIDATE_VERIFICATION.json`。能力提升尚待新运行；State创建未登记等启动/传输问题与模型输出错误分开统计。

另已登记 G1k 13.3B 下载、NAS 上传、格式适配和 G1j/G1k 能力对照任务：`G1K_FOLLOWUP/PLAN.zh-CN.md`、`TASK.json`。官方文件为 [rwkv7-g1k-13.3b-20260930-ctx25600.pth](https://huggingface.co/BlinkDL/rwkv7-g1/blob/main/rwkv7-g1k-13.3b-20260930-ctx25600.pth)，固定 revision `cd67fb95fa9e2ce8757f8d21d713e74a9c788118`，26,540,868,485字节，SHA-256 `31799b3f8207e74c1b47f359184ac1c658c927ff697971447f7bf0fd18ae393f`。传输状态以 `TRANSFER_STATUS.json` / `DOWNLOAD_PROGRESS.json` 为准，完整本地与 NAS 校验回执生成前不记为完成。

新模型尚未进入 Agent 对照。先完成当前 G1j 阶段，再固定共同代码/题集/预算；相同格式和额度下的模型对照、格式候选对照、完整上下文实验分别报告。官方当前指南适用于 G1 系列，G1k 特有格式偏好与收益仍须实测。约束解码持续作为默认配置，旧 State 未验证兼容不得复用。当前工具环境没有新建 Codex 任务接口，后续任务保存为仓库内独立持久登记。

## 缺陷与后续数据入口

`ERROR_CATALOG/README.zh-CN.md` 为全量目录；`OCCURRENCES.jsonl` 保存每个错误/拒绝/重复事件，`ALL_CALLS.jsonl` 保留正常及异常返回索引，`CASES/` 和 `UNCOMMITTED_RETURNS/` 保存原文。`ARTIFACT_REVIEWS.json` 对照逐题文件、入口、语法、实际运行回执和工作声称；`DEFECT_CARDS.json` 给出已核实根因，`DATA_DESIGN.zh-CN.md` 说明针对性能力和待审查目标。

优先问题：保留用户公开契约；准确引用回执/SHA并在拒绝后修正；通过真实启动/功能验证指导实施；区分正常长代码与重复正文；根据真实缺项完成收尾。工程侧优先统一三种编辑工具 SHA schema 与执行校验，前置 Planner 实际输入预算检查，明确未提交返回的审计边界，并修正检查误判与事实投影。Controller 不代选动作，不补写模型完成证据。

这些是开发评测错误材料，当前训练准入 false、训练行0。后续纠正需独立审查；工程异常不能直接转为模型训练标签，当前评测私有答案保持隔离。生产修复尚未实施，收益须经新冻结运行验证，当前分数不重算。

## 当前架构

完整目标→Decision 基于证据选择直接执行或强模型规划→Executor 持续执行与局部修正→独立检查→Decision 判断目标满足→完成门。原目标、模型设计与可执行检查分开；Controller 只校验权限、真实回执、State 身份和完成条件，不代选动作。

唯一当前协议：Ledger v10、Goal v1、Plan v5、Assignment v6、Planner v14/chat v3、Decision v17、Executor v13；prompt v7、输入传输 v2、格式适配 v6。Planner 只读批次保留原参数、顺序和逐条回执；同次输入完整相同文字可逐字共享。Native exact-token 预填充与真实清理生命周期已验证，旧 State 不静默复用。当前继续 G1j 分支。细节只在[架构](ARCHITECTURE.zh-CN.md)维护。

## 回归、源码与发布边界

生产源码、通用脚本和测试集合/SHA 与完整本地回归相同，沿用2910通过、0跳过、722.10秒的记录，未声称重新运行；十二题套件合同专项2通过。owner既存未提交研发改动保持。公开提交源码的构建/入口检查与包含这些改动的完整工作树回归分开，CI不替代完整回归。

公开分支 `chase/g1j-agent-improvement-public` 只发布维护源码、架构文档和必要构建配置；实验、测试、trace、生成产物只保留本地，见[发布规范](SOURCE_DISTRIBUTION.zh-CN.md)。本阶段先发布完整120题基线文档，再应用已审查候选并开始新六题工程验证。原十二题与新增108题服务/隧道均已停止，最终journal和State审计证据保留。远端Git、Holdout、OA、训练、新datasets版本均未操作。
