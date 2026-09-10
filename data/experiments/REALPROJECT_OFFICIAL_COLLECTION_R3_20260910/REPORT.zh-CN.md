# REALPROJECT_OFFICIAL_COLLECTION_R3_20260910

Agent **Strict 0/12、completed 0/12、mutation 0、动作 43**。全部 12 题保留原分母，运行 3330.93 秒；源码 e7c455b6、题集、评分、参数全程不变。终止原因：7 题重复成功动作无进展、2 题工具/参数协议拒绝、1 题 Native create 结果未确认、1 题 Step Auditor 协议拒绝、1 题重复失败动作。实际 optimizer steps **0**，未创建正式角色数据版本。

## 官方 Planner 的实际表现

Planner / Stage Checker 使用官方 DeepSeek V4 Pro，显式 thinking=enabled、reasoning_effort=low。最大输出分别 32768 / 16384，读取预算 600 秒。12 题全部得到已接受的初始计划，共 21 次计划请求、5 次阶段检查；没有 Strong 请求失败。存在 4 次计划补丁语义拒绝及后续纠正，不能把 HTTP 成功等同计划永远正确。相较旧第三方网关轮的 10/12 HTTP 500，本轮执行已经进入各题角色链路。

## 真实首错及传播

API-01 的 S1 要读取 README 提取完整接口要求，Selector 选择 search_text，Executor 搜索 README 字样，仅得到一行；Step Auditor 却判 S1 完成。S2 要读取 server.py，模型仍选择搜索并把文件名当搜索词，连续返回零匹配。S2 的 REPAIR 反馈已绑定原步骤与证据传回 Selector / Executor，没有触发 Planner 重规划；模型继续重复相同操作，最终无进展阻塞。原始证据及事件身份见 `RP-API-01.FAILURE_CHAIN_OBSERVATION.json`。

WEB-02 进入 execute，模型发出合法的 `python3 -c ...` 环境检查。Harness 却将项目 venv 中找到的任何可执行文件都当作 Python console script，把命令改为 Python 解释器读取另一个 Python 二进制。实际错误为 `SyntaxError: source code cannot contain null bytes`；5 次重复失败导致终止。此处根因在通用命令解析，不能归为模型参数能力，也不能靠 StateTune 掩盖。下一工程轮须按文件的实际可执行身份和解释器声明修复，不追加 python3 名称特判。见 `RP-WEB-02.FAILURE_CHAIN_OBSERVATION.json`；本轮不会修改后重评分。

CLI-02 在已完成的角色生成之外，另有一次 `RWKVOutcomeUnknownError`：Native create 结果未确认，request_id 为 `NR-912a82290ad4bd0a7059d08b43c4f01cd23840e446a94126df0248801910009d`。本轮保留中断，不把未确认请求计成完成或自动重放；具体服务端原因需另行核实。

## 交接与角色数据

Selector 56 个真实选择边界、168 个菜单求值。Executor 78 次生成，Step Auditor 39 次，Finalizer / Final Auditor 均未到达。全部已返回的 **117/117 Native 完整输入 token、117/117 角色输入字节**通过当前唯一 builder 与 durable checkpoint 核验；该结论不包括没有确认结果的 create，也不证明语义判断正确。

本轮自动 Selector 标签 69 条，train 67 / dev 0 / confirmation 2，另 99 条待复核。单独本轮缺 mutate / missing_target 与 dev，不构成合格数据集。

按原注册范围合并 UltraData R6 与本轮全部 15 个来源后，共 **81 条自动标签：train 76 / dev 3 / confirmation 2；126 条待复核**。execute 15、mutate 12、missing_target 9、py_root 21，原登记角色覆盖和非空切分均通过。386 对跨切分比较中 113 对超过原 0.95 阈值，候选仍为 INVALID。没有改 family、相似度算法、文本字段、阈值或评价口径；没有删除失败来源、伪造复核或补造后续阶段。

由此，当前数据障碍已不再是角色边界总数或没有任何 execute，而是跨切分污染及错误选择标签的独立复核。低 Agent 分数不构成首轮训练禁令。已提交的九边界复核包仍未批准，owner 的复核方式问题保持待答；训练本身的既有授权继续有效。

## 验证边界与证据

本轮代码沿用此前完整 **1414 passed、0 skipped** 的冻结源码。12 题私有行为验证器均在原隔离流程中调用，4 道 Web / 全栈均按 browser 要求启动验证流程，实际 exit code 均为 1；2 道 Web 留有 Playwright 诊断。browser 标记本身不证明浏览器验收通过。只读执行元数据见 `VERIFIER_EXECUTION_METADATA.json`，未读取私有验证程序或期望值，未重评分，Real Agent Holdout V2 未读取。

所有原始结果、SQLite、完整请求/响应和状态证据保留在本地 `all_zero/cases`，受现有 Git ignore 规则控制；路径和 SHA 均收入 `EVIDENCE_SHA256.json`。摘要、候选审计和清单本地提交，owner 负责 push。
