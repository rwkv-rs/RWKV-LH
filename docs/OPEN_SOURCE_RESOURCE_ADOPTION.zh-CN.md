# 外部开源资源接入判断

核查日期：2026-09-09。Agent 没有新增完整评测成绩；正式 optimizer steps 为 0。本轮完成资料核查与接入设计，没有把外部轨迹登记为当前生产 trace，也没有下载完整训练集。抓取来源、失败记录及论文 SHA 见 [核查记录](../data/experiments/OPEN_SOURCE_RESOURCE_REVIEW_R1_20260909/SOURCE_FETCH.json)。

| 资源 | 已核实的发布内容 | 对 RWKV-LH 的用途与限制 |
|---|---|---|
| [RSI-Harness](https://github.com/CosmosMind-ai/RSI-Harness) 与 [MetaRSI-v1 论文](https://www.cosmosmind.ai/research/metarsi-v1.pdf) | 仓库是 Pi + Genome 配置层；当前 README 明确不包含基准、数据生成、训练或评测代码。论文讨论数据、Harness、模型三种改进面的调度。 | 借鉴稳定内核、声明式配置、改动后重新采集证据、冻结评测与实验账本。不能将开源 Harness 当成已可运行的完整 StateTune 系统；论文的自我教学实验不要求我们取消独立强模型 Planner。 |
| [MiniCPM5-2B](https://huggingface.co/openbmb/MiniCPM5-2B) | Transformer 模型与多阶段检查点，模型卡给出 `LlamaForCausalLM`。 | 可用于独立对照与研究小模型的数据配方。它不是 RWKV，权重、KV cache 与 RWKV 初始 State 不能直接互换；本轮不更换五角色架构。 |
| [UltraData-SFT-Agent-2609](https://huggingface.co/datasets/openbmb/UltraData-SFT-Agent-2609) | 数据卡宣称 483,661 条轨迹，包含工具使用、代码、搜索和通用 Agent；不是独立任务数。仅有静态轨迹，没有运行环境、工具实现、测试或采样代码。 | 优先审查 Tool-Use / Code-Agent 的错误恢复、工具选择和逐轮质量信息；可作为行为分析及任务来源线索。无法直接复现其验收，也不能重命名工具后冒充当前五角色的合格 trace。 |
| [UltraData-RL-2609](https://huggingface.co/datasets/openbmb/UltraData-RL-2609) | 数据卡宣称 85,995 题，其中 Code 23,665 题；Code 提供标准输入输出测试，未提供沙箱。 | 更适合首个外部可执行任务试点：保留原题及来源，用现有沙箱独立执行测试，让当前 Agent 实际完成任务后抽取角色边界。Math 等题可补充可验证推理任务，不能自动成为 Selector 标签。 |
| [Meshy](https://github.com/OpenBMB/Meshy) | 以 SGLang、torchtitan、TransferQueue 组织独立 rollout、训练、推理服务。 | 借鉴数据就绪触发、背压、任务身份和 GPU 资源调度。其服务角色不是本项目五个模型角色；现有 Native RWKV / State-only 训练需要单独适配与数值验证，当前不整体迁移。 |
| [JustRL II](https://huggingface.co/openbmb/JustRL-II-base-model) | 官方模型卡说明发布的是 RL 初始化检查点，配方使用 critic 与长度适配的优势估计，研究长推理强化学习。 | 借鉴题目可验证性、标签复核和难度校准。GRPO/critic 不是当前 StateTune 监督目标的直接替换，不增加生产 Auditor 的额外 Head；先完成现有采集与 State-only 优化链。 |

推荐先处理两个层次。工程层采用单一配置、明确错误归属和冻结的运行身份，本轮 Planner 修复已经落实。数据层优先核查 RL Code 的真实发布文件与来源，再登记有界采集试点；Agent 轨迹先作为诊断资料，有可重建环境与独立验收时才进入执行采集。

外部任务的接入路径是：固定来源 revision / 文件 SHA / 原始任务标识 → 核查材料、执行条件与验收 → 在当前 Harness 中实际运行 → 按当前角色唯一 builder 重建 trace → 冻结角色回归与覆盖指标 → StateTune。必须保留外部来源与当前 run 的关联；作者参考答案和独立验收材料不进入 Agent workspace。缺失环境不能编造为已复现；公开静态对话缺少 RWKV token / BOS / State 身份，不能直接补成生产证据。

两份 UltraData 数据卡列出 Apache-2.0，同时要求遵守上游来源条款，并列出再发布限制。因此本轮只提交链接、核查结论与 SHA，没有将外部全文或数据集镜像提交进仓库。数据卡统计是发布者声明，尚未逐文件清点；不能据此认定可用样本数或角色覆盖率。

[RSI-Harness 的 Hugging Face 链接](https://huggingface.co/CosmosMind/RSI-Harness) 本轮未成功取得内容；两个 Notion 博客只取得页面外壳，Meshy 与 JustRL II 的判断分别以官方 README 和模型卡为据。论文 PDF 已取得并提取 47 页，SHA-256 为 `20ff687ad2356a5d3859f3281518d7b8d088cf17dc00b8cec027176e25069190`；发布方性能数字尚未在 RWKV-LH 独立复现。
