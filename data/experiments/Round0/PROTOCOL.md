# Round0：RWKV-E2E-90 十轮实验预注册

## 1. 目的

本目录是 Round1～Round10 的不可变实验入口。目标不是用程序规则把答案做对，而是观察
RWKV 在不同通用架构下真实产生的输入、输出、动作、状态变化和最终结果，据此更新 RWKV-LH。

Round0 只冻结题目、标准答案、指标、运行参数、数据血缘和非干预边界，不计入十轮成绩。

## 2. 固定题集

正式模型题集为 RWKV-E2E-90，90 个 case id 全部唯一：

- Basic 30：原 E2E-B01～E2E-B10 + 新 E2E-B11～E2E-B30。
- Medium 30：原 E2E-M01～E2E-M10 + 新 E2E-M11～E2E-M30。
- Hard 30：原 E2E-H01～E2E-H10 + E2E-LH01～E2E-LH12 + 新 E2E-H11～E2E-H18。

E2E-LH 保留 native level=long_horizon，汇总榜固定映射为 Hard。不得复制同题、重复运行后
按次数冒充新题，或在轮次间替换失败题。

权威文件及 SHA-256：

| 资源 | SHA-256 |
| --- | --- |
| benchmarks/rwkv_e2e/rwkv_e2e_30/tasks.json | 0bf73c9a86bd014f5a94e5686ffe744bbef6c560f4227e37d0b753b900481c4c |
| benchmarks/rwkv_e2e/rwkv_e2e_30/acceptance.json | c4953c556a9ba2e080493f34bb2261db349080542376c4e94f08d5227e0f74cd |
| benchmarks/rwkv_e2e/rwkv_e2e_lh12/tasks.json | d813a7bc3a42e27ee3573ea342a918bd7ee5347ca8b0e893c04fded262457a5e |
| benchmarks/rwkv_e2e/rwkv_e2e_lh12/acceptance.json | 976e075bcc81780ed38ce7b9fe8c6c19c1b239bb72595ce176308f2760a0cd9f |
| benchmarks/rwkv_e2e/rwkv_e2e_extension48/tasks.json | 384d52b5395dbcb31947dbfd1cfe63167ccbe68ed8b03e675fddc32ffd25ec7b |
| benchmarks/rwkv_e2e/rwkv_e2e_extension48/acceptance.json | 395e1651f52259de7e56a63476504891f136edd2d4dd5a8263064077741ede12 |

LH-Control-30 每轮都运行，但只作为确定性架构门禁，不计入 RWKV 的 90 题成绩。

## 3. 标准答案

Codex 在任何 Round1 RWKV 输出产生前，依据可见题面独立完成并冻结 90 题参考结果。参考结果
保存于 data/datasets/rwkv_e2e_90_v1/codex_reference_answers.json，其摘要写入同目录
manifest。冻结后不得因 RWKV 的答案修改参考答案、检查条件、相似度算法或阈值。

标准答案和 acceptance 只能在模型运行结束后用于评分，不得进入 RWKV 的 prompt、working
memory、recovery context、候选选择或最终回答生成。

## 4. 非干预边界

必须由 RWKV 决定：

- Goal 解析与成功条件表达；
- 任务拆分、动作类型、动作参数；
- 基于观察的下一步、重试、恢复和 replan 意图；
- 最终回答。

程序只允许：

- 原样发送已登记 prompt，记录固定采样参数；
- 解析协议结构；解析失败可原样反馈给 RWKV 自修或记为失败；
- 分配内部 ID、持久化事件、执行 RWKV 选择的工具；
- 执行与答案无关的工作区、安全和幂等边界；
- 在运行结束后读取隐藏标准进行评分。

程序禁止：

- 根据 case id、题面关键词、参考答案或 acceptance 选择动作或参数；
- 用规则生成 RWKV 漏掉的语义值、文件内容、计划或答案；
- 生成多个答案后按隐藏标准挑选；
- 用其他模型替 RWKV 规划、修复、裁判或代答；
- 删除、增加、改写、排序或替换 RWKV 最终回答。

raw_rwkv_final_output 必须与 delivered_final_output 字节完全相同。规范化文本只可作为并列
审计字段，不能覆盖原始输出。

## 5. 固定运行条件

- 执行环境：WSL UbuntuRecovered。
- 模型：rwkv7-g1i-13.3b-20260805-ctx16384。
- 推理端：vllm-rwkv，开跑前必须保存 doctor/capability 结果。
- max_transitions=200。
- case 隔离进程并发：8；若硬件原因变更，所有对照轮必须同样重跑，不能只改候选轮。
- 采样：以 TemperaturePolicy 和 RWKVSettings 的轮次快照为准；十轮期间除非把采样本身
  作为预注册单变量，否则不得改变。
- 工具、题目、初始工作区、超时和 acceptance 固定。

## 6. 固定指标

主指标：

1. External acceptance rate，90 题和 Basic/Medium/Hard 各组分别报告。
2. Strict E2E rate：Agent completed、external passed、最终回答非空、最终回答非干预、
   verifier 隔离均满足。
3. Agent/external false positive 与 false negative。

诊断指标：

- 模型请求数、输入/输出 token、时延；
- task、attempt、retry、reselect、replan 数；
- 协议错误、解析修复、重复失败 lineage；
- 每阶段 prompt、raw output、parsed payload、tool input、tool output、validation、
  state revision 的因果链；
- 通过题的 exact artifact similarity；
- 固定 utf8-byte-ngram-cosine.v1（UTF-8 byte 5-gram cosine，n=5）；
- 近重复阈值固定为 0.95。

不得用主观“看起来更好”替代这些指标。

## 7. 每轮目录与完成条件

每一轮固定写入 data/experiments/RoundN/：

- RUN_PROTOCOL.json：题集摘要、代码 commit/diff、采样、endpoint/model、并发和预算。
- runtime_doctor.json：服务、capability、模型和 tokenizer 状态。
- cases/case-id/audit.json：完整模型输入输出与程序转换。
- cases/case-id/workspace/：最终外部可观测产物。
- results.json、REPORT.md。
- causal_analysis.json、CAUSAL_ANALYSIS.md。
- comparison_vs_previous.json。
- STRUCTURE_CHANGE.md：只记录由前一轮全量数据支持的通用根因和单变量修改。
- lh_control_30/ 与离线测试结果。

一轮只有 90 题全部产生终态、记录完整且 Control-30/离线回归执行后才算完成。运行中断的题
仍计失败并保留数据，不能静默丢弃或只重跑失败题替换原结果。

## 8. GitHub 回档

候选结构只有在同一固定口径下满足以下条件才提交并推送当前功能分支作为回档点：

- external acceptance 高于此前最佳；
- false positive 不增加；
- 非干预检查全部通过；
- 90 题、Control-30 和离线回归全部完成。

提交信息必须包含 RoundN 和核心指标。没有提高则保留实验数据和分析，但不把候选结构标记为
新的最佳版本。
