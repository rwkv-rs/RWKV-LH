# 任务结果审核规范 v1

目标是建设 RWKV 专属 Harness 与可用 Code Agent。审核回答的是交付是否满足用户目标；成本、延迟和吞吐只能在同等质量下比较。本规范用于当前能力诊断及后续公开开发任务，不改写历史实验、私有验收或模型输入协议。

## 判断对象与规则

运行前冻结原始用户要求、文件快照、验收契约、模型/协议/源码、采样、State 初始化、预算和错误恢复策略。每项必要条件必须绑定用户原文，说明遗漏对使用结果的影响；参考实现和摘要要点仅在外部审核保留。

- 必要结果：用户明确要求的用途、重要行为与限制。按独立结果分别记录满足、部分满足、未满足、未审核。
- 可省略细节：实现语法、超时、连接关闭等，除非用户明确要求详述。遗漏不否决任务，写错仍需记录事实问题。
- 事实忠实性：引用原答案和来源证据，区分轻微表述问题与影响主要理解的实质错误。不得把遗漏自动标为编造。
- 路径自由：不要求参考工具顺序、调用次数、关键词或逐字答案。重复调用、恢复后的非法参数属于诊断和成本；最终正确交付不因走法不同失败。用户明确的只读等约束仍需核查。
- `final_answer` 表示提交，不表示通过外部验收。错误工程声明须有原文和反证，例如未运行测试却说测试已通过。

| 任务状态 | 含义 |
| --- | --- |
| met | 必要结果满足，无实质事实问题 |
| partially_met | 有可用成果，但必要结果部分缺失 |
| not_met | 必要结果未满足，或有实质事实错误 |
| no_delivery | 没有答案或交付物；内容质量不适用 |
| invalid | 用例/夹具/评测条件无效，有具体证据 |
| unreviewable | 缺少判断所需证据或必要审核 |

总数、有效数、无效和证据不足数量同时报告，后两者不悄悄消失。有效分母包含未交付和失败。先报告任务结果、提交、实际修改、终止原因，再报告调用/token/协议/State 数字，不称为项目 Strict。

## 实验性质与归因

`task_trial` 必须给模型真实协议错误反馈并允许预算内自我恢复；遇第一次错误立即停止的运行只能标为 `boundary_probe`。反馈不能替模型修参数。旧实验按原 stop 规则保留，不推断它已经测试完整恢复能力。

区分模型可观察行为、Harness 输入、工具、State、基础设施和评测设计。每条归因登记 observed/hypothesis/confirmed 与证据。输入大、答案短或一次失败都不证明根因。强模型辅助明确登记独立完成、建议后完成、接管完成；审核者不能仅凭执行模型名称推定独立完成。

质量门采用预登记完整任务×重复次数网格，同一任务契约与执行身份一致。固定组连续两遍全部合格仅说明组内表现。零非法参数等可单列可靠性门，不能倒过来改变交付质量。相对收益另登记：基线 7/8 而要求提高 2/8 属于天花板受限，不能据此说候选能力失败。历史回顾不能作为新收益。

## 可执行入口

统一模块为 `rwkv_lh/task_review.py`；入口为 `scripts/review_agent_task.py`。所有输出只允许新建，契约、原始运行、审核意见互相绑定 SHA；聚合时重新核验来源文件，不直接信任一个旧分数。

```bash
.venv/bin/python scripts/review_agent_task.py freeze --input contract-draft.json --output contract.json
.venv/bin/python scripts/review_agent_task.py capture --input capture-job.json --output run.json
.venv/bin/python scripts/review_agent_task.py packet --input review-job.json --output packet.json
.venv/bin/python scripts/review_agent_task.py assess --input review-job.json --output assessment.json
.venv/bin/python scripts/review_agent_task.py aggregate --input batch-job.json --output summary.json
```

review-job 包含 `contract/run/judgment/evidence_root` 路径，packet 不需要 judgment；路径相对 job 文件。batch-job 是 `{"reviews": [review-job, ...]}`；gate 操作另需 task_ids、repeats、arm。capture-job 包含 directory、task_id、arm、repeat、protocol_error_policy、execution_identity、historical、assistance，后三种归属为 rwkv_independent/strong_advised/strong_takeover。execution_identity 的 model/protocol/source/sampling/state/budget 六个 SHA 必须有可查原始登记，不能填占位值。

当前 capture 适配已使用的直接诊断 trace，只接受生产 parser 验证且已 commit 的原始 final，原文不改写。其他运行器应产生同一 run 结构并绑定交付快照与真实 trace，不能把不兼容的日志强行套入该适配器。

程序验证结构与证据绑定，语义判断仍由人或独立审核者逐项给出，不能靠结构校验宣称判分客观无误。有争议时保留意见，标记证据不足，下一轮澄清；不能临时改门后宣称收益。审核不是 RWKV 执行链的逐步强模型关卡，不把要点传入模型，不直接转成训练标签。

## 当前四类任务的粒度

- 健康实现：定位、健康响应、其他 GET 响应各自审核。用户问返回什么，返回行为是必要结果；不要求具体 if/json 写法。
- 健康脚本：定位、健康检查用途、业务验证边界各自审核。概括健康请求成功可表达主要用途；精确断言、超时、关闭细节允许省略，但不能明确否认脚本真实检查。含“只做 200”这类排他措辞需单独记录其不精确影响，不能当作无瑕疵摘要。
- 数据库校验：定位、完整性、版本和结构检查分别审核。允许不列逐个列名，不允许称未实现的内容验证已实现。
- 独占备份：定位、创建方式、目标已存在行为、临时清理分别审核；后三者由用户逐项点名，不能作为一般细节省略。

运行契约还须登记只读约束；文件摘要则以主旨、重要行为、重要限制为必要项，不把所有实现细节捆成事实组。当前保留旧原始评分；回顾实例在 TASK_OUTCOME_AUDIT_REFORM_R1_20260913。下一次推理必须使用本入口形成外部结果记录，先冻结新运行身份与上述粒度，恢复输入问题诊断，不升级复杂任务。
