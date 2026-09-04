# RWKV-LH 当前交接

更新时间：2026-08-31（Asia/Shanghai）

## 不可破坏的约束

- 只在 WSL `UbuntuRecovered` 的 `/home/chase/GitHub/RWKV-LH` 执行项目命令，使用 `uv`；临时脚本放在绝对路径 `/home/chase/GitHub/RWKV-LH/temp/`。
- 训练、Selector 与 Executor 实验固定物理 GPU0，不因为其他 GPU 空闲而迁移。
- strong model 只做 Planner/Reviewer；2.9B 只选 operation；13.3B 只做参数、执行推进和总结。
- Selector/Executor state 独立持久化；一个 task 内不得切 state。先做固定联动消融，再决定最少 profile。
- 绝不诱导、修改、删除、补全、截断、重排、隐藏或替换 RWKV 原始输出。无效输出也先 append raw，再记录显式拒绝。
- 不得用静态 Selector 指标冒充真实 Harness 能力，也不得用旧 Full90 冒充整体 Agent 能力。
- Agent Ladder 是 holdout；它的请求、路径、验证器文本不得进入 state-tuning train/dev。
- 工作树已有大量用户实验与改动，只触碰本轮登记文件，保留无关内容。

## 当前服务

### 产品 Executor

- 本地 tunnel：`127.0.0.1:29610` → `rwkv-8222:18070`。
- 远端服务当前健康，物理 GPU0，GPU UUID `GPU-1faf7f09-25f4-2515-b707-6e0766aa841d`。
- served model：`rwkv7-g1i-13.3b-rwkv-lh-stage8-r3-step1700-bos-ctx2496`。
- 该进程只用于产品连续性/历史对照；不要停止、替换或把它解释为当前 G3/G6 候选。

### 实验服务

- 远端 `18075` 当前运行最佳 G3/G6 multi-profile R7 服务，API PID `3321608`；本地
  `127.0.0.1:29613` tunnel 可达。
- served model：`rwkv7-g1i-13.3b-exe-g3-g6-deterministic-cmix-r7-multiprofile-ctx2496`。
- Selector `127.0.0.1:29621` 当前健康，S60/zero，物理 GPU0；launcher 为
  `scripts/run_network_selector_s60_requirement_byte_tail_zero_service.sh`，当前 PID `2541809`。
- Web `http://127.0.0.1:8766` 当前 PID `2554449`，使用 `rwkv_lh/goal_web_assets`；主动 worker PID `2542018`。页面默认
  `contract_graph + auto_public`，可手工改为 offline；顶部如实显示 canary 0/3。
- `RWKV_RUNTIME_MODE=external`；stack 只拥有本地 Selector/Web/worker，不停止外部 18075
  或旧 18070。
- 0.4B Shadow 已从运行栈配置、进程拓扑和前端删除；历史源码/记录仅审计。
- 当前没有 `train.py` state-tuning 进程。

### Planner 配置

- ignored `.env` 已固化：`gpt-5.4-mini`、无 fallback、全 phase reasoning `none`、transport retry 2、contract plan/review token 上限 4000/2400。
- plan cache 在产品配置可开启；真实性探针与 canary 关闭 cache。
- API key 和 Tavily key 只从 ignored `.env`/`.env.local`/进程环境读取，不得复制到文档、结果或终端摘要。

## 当前正式实验绑定

- Selector：2.9B G1i，S60 v7 requirement-byte-tail，Hidden(mean+last)+h64 MLP，zero state；head SHA-256 `721669ce8733b590b3aa6c910d8bc13d744612f1fee884d5276a3f0d96d0d441`。
- Executor base SHA-256：`5d97772ba04a81bdaeba90e1d6d306c70560bf4f784522be61cdcade69e30562`。
- Offline/general：`EXE-G3-MULTISTAGE-STEP2000`，SHA-256 `13f6586951666962405286dda8e45c1eae82a37c68c21b3b75dbbb04c6e54f12`。
- Network：`EXE-G6-NETWORK-RECOVERY-STEP1500`，SHA-256 `611d9e5564ef47413c1bd1536500e987270c8303b2c87d5d54bca256d57dd68b`。
- 每次实验必须记录 model/profile ID、SHA、physical GPU、remote launcher/overlay identity 和 run 内 switch 数。

## 本轮已完成

- Retrieval Quality R2：9/9，top1/recall/host precision 均 1.0，重复率 0，p95 6.587s。
- 冻结 Agent Capability Ladder V1：10 题、5 层、独立 verifier；reference 10/10；与当前 G3/G6 的 byte 5-gram 最大相似度 0.131，小于 0.95。
- 基线 R2：strict/external/completed 均 0/10；7 个 Planner 500，3 个真实 RWKV 事务失败。
- capability projection v3、预算、全部写根覆盖、依赖 verifier、Planner 写根预算已实现。
- Planner 全 schema 探针：`gpt-5.4-mini + none` 在简单和中型请求均 1 次 HTTP 严格 JSON 成功。
- 缺陷 canary：结构门通过，Planner failure 0/3，40 个 v3 atom，10 次 fail-closed，69 个 raw generation 完整性全过；strict 仍 0/3。
- 独立复审的 4 个 P1、3 个 P2 已全部修复：finalizer 全证据依赖、独立 final-presentation gate、来源扫描
  fail-closed、exclusive snapshot transaction、pending resolved 生命周期、child attempt 幂等恢复、
  Contract Graph Shadow 统一投影。
- 固定失败注入矩阵 7/7；相关回归 177 passed；全量回归 684 passed，1 个既有 Python 3.13 fork 弃用 warning。
- S71 2K state tuning 完成 ST500/1000/1500/2000 消融，四个候选均低于 zero，已拒绝且未接入。
- 当前完整单元测试为 706 passed、1 warning；4P1/3P2 相关闭环回归 180 passed。
- 当前最佳三题真实 canary 已完整运行：completed/external/strict `0/3`；Planner failure 0，
  RWKV 242，Action 73，protocol reject 144。联网题 7/7 次 web_search 成功，但项目未闭环。
- 242/242 raw generation byte/SHA 一致；227/227 Selector handoff 为未后处理的 eligible argmax；
  三题 profile switch 0。
- 修复 Supervisor `.env` 跨命名空间污染：Supervisor 只加载 `SUPERVISOR_*`，产品显式固定
  progressive disclosure。修复后的真实 Web run `UI-20260830-233140-0dadf4` 成功完成
  `calculator → final_answer`，最终 `4` 与持久 RWKV 输出逐字一致；这只是部署烟测，不覆盖 0/3。
- 产品 29610、最佳 29613、Selector 29621 均健康；没有停止旧产品、训练 state 或使用 GPU1/2。

关键证据：

- `data/experiments/LOCAL_AGENT_CAPABILITY_LADDER_V1_20260830/run_current_s60_g3_g6_baseline_v1_r2/BASELINE_RESULT.json`
- `data/experiments/AGENT_HARNESS_TRANSACTION_REMEDIATION_V1_20260830/REMEDIATION_RESULT.md`
- `data/experiments/AGENT_HARNESS_TRANSACTION_REMEDIATION_V1_20260830/run_bugfix_canary_v1/BUGFIX_CANARY_RESULT.json`
- `data/experiments/LOCAL_RETRIEVAL_QUALITY_V1_20260829/run_r2_post_r7_20260830/RESULT.json`
- `data/experiments/HARNESS_CAUSAL_CLOSURE_P1P2_V1_20260830/PREREGISTRATION.md`
- `data/experiments/HARNESS_CAUSAL_CLOSURE_P1P2_V1_20260830/RESULT.md`
- `data/experiments/HARNESS_CAUSAL_CLOSURE_P1P2_V1_20260830/MANIFEST.json`
- `data/experiments/NETWORK_SELECTOR_DIVERSE_BOUNDARY_S71_V1_20260831/RESULT.md`
- `data/experiments/FAST_AGENT_CAPABILITY_CANARY_V1_20260831/RESULT.md`
- `data/experiments/FAST_AGENT_CAPABILITY_CANARY_V1_20260831/DEPLOYMENT_SMOKE.md`

## 已确认的剩余根因与待复验边界

- 静态 S60 分类超过 96%，但真实 Contract Graph 轨迹仍会把 read/investigate 选成
  `date_diff/calculator`，把文件创建选成 `write_json`。
- 13.3B 会为错误 operation 生成形式合法但语义错误的参数；例如把 `pricing.py` 写成 JSON，
  或反复写同一个 JSON 而未覆盖多写根。
- 当前失败样式包括：L1 缺 README/verify；L4 多轮未创建任何网页文件；L5 检索成功、snapshot
  完整，但六个项目写根未覆盖，失败 transaction 没有合并。
- Harness 现在拒绝提交这些输出，因此下一步属于模型 state tuning，不能通过隐藏 `final_answer`、改写 raw 或 Controller 补动作来修饰。
- 上述三题残差来自 P1/P2 修复后的固定 canary；尚未重跑冻结 10 题完整 Ladder，因此不能把
  三题结果外推为完整层级分数，也不能直接把所有剩余失败归因于 state tuning。

## 下一执行顺序

1. 保持当前最佳预览服务；前端部署闭环已经验证，但不要把简单手工成功改写成发布分数。
2. 从最新 242-generation 残差生成不同实体/路径/措辞的约 2K 数据，禁止复制 Ladder
   请求、文件名、路径或 verifier；固定 byte 5-gram cosine v1/0.95 去重门。
3. 在物理 GPU0 固定做 Selector zero/tuned × Executor G3/G6/候选 transaction state 联动；
   只有真实 canary 提升且联网/工程留存不回归才保留。
4. 代表性 canary 达门后再跑完整 10 题 Ladder；在此前整体 Agent 仍标为实验预览。

当前状态入口见 [CURRENT_STATUS.zh-CN.md](CURRENT_STATUS.zh-CN.md)。
