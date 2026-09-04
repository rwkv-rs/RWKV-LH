# RWKV-LH Action State Tuning Round 1 / 2K v1 预注册

日期：2026-08-26（Asia/Shanghai）

## 目的

第一轮只改变 RWKV 的初始 recurrent time-state，训练模型在当前 Harness 暴露的真实状态下做
正确的下一步决策。数据不是通用任务 SFT，也不以“多做一些任务”为目标；每条样本必须对应
历史运行中已经观测到的一类错误状态迁移。

本轮完成后立即部署独立 endpoint，并复跑全部已登记缺陷。下一轮数据只针对本轮后仍存在或
新出现的错误，不在本轮预先堆量。

## 训练单位与精确规模

- 主训练文件：恰好 2,000 条 generation-boundary stage SFT。
- 独立 dev：200 条，不进入训练。
- train/dev 以 semantic family 切分，family、实体、路径命名空间零重叠。
- 每条 target 是当前 progressive G1i 协议中的 selector 或 direct generation；prompt 必须由
  当前 Controller/ModelSession 真实回放捕获。
- 只对 `Assistant:` span 计算 loss，服务器使用 `--data_type jsonl --loss_mask qa`。

## 首轮配比

| failure cluster | train | dev | 直接来源 |
|---|---:|---:|---|
| 协议拒绝后的同合同纠正 | 400 | 40 | Round118：66/90 case、299 次拒绝、18 case 耗尽预算 |
| 零进展抑制与有证据的恢复/停止 | 450 | 45 | Round118/119/158/162 的成功循环、失败循环与 stagnant 簇 |
| Observation 到下一动作/参数的逐字绑定 | 400 | 40 | ECRA R9 111/118、Round118 B12/M29 |
| 集合 coverage 与阶段 focus 继续推进 | 350 | 35 | Round118 H02/H12/H14/LH03/LH11，Round119 成功循环 |
| 完成边界、新鲜验证与剩余义务 | 300 | 30 | Round118 35 FP、Round158 4 FN、Round162 typed-view/recovery 分类 |
| 不可信/秘密值到 Gate 的可达性 | 100 | 10 | ECRA R9 privacy rejection coverage 0.5 |
| **合计** | **2,000** | **200** | |

配比按观测频率、影响范围和安全严重度预注册，不在生成后按结果调权。工程层缺陷不得为了凑数
映射为 RWKV 标签。

## 样本结构要求

每个 stage audit 至少登记：

- `failure_signature_id` 与来源报告摘要；
- 可见 state features；
- 历史错误 transition；
- 本条正确 transition；
- 至少一个 hard negative；
- private oracle digest、Controller replay 结果和 target parser 结果。

强模型只允许生成虚构场景表面，不得生成 operation/params/final label。operation、参数、完成边界
和正负判定全部由 failure registry、本地 oracle、ActionHarness 与冻结 verifier 决定。

## 明确排除

- Strong Planner schema/transport failure；
- lease fencing、HTTP response close、terminal ownership 等工程并发/资源问题；
- typed contract compiler 或 evidence-store 投影自身的错误标签；
- 冻结 ECRA route120 与 E2E90 的 request、reference answer、URL、实体或目标文件内容；
- 旧 operation-selection 数据中的已废弃 `lh_select_operation` 正标签；
- 旧 480 pilot 的机械复制，及已中止 10K 生成器的任何临时行。

## 数据闸门

- train/dev stage 数严格为 2,000/200；
- target parse、Controller replay、literal/state binding：100%；
- exact `text` duplicate：0；train/dev family overlap：0；
- 每个样本均有有效 `failure_signature_id`，cluster 配比严格一致；
- state-feature cell 覆盖达到 manifest 中预注册矩阵的 100%；
- privacy backend execution：0；
- 对冻结 210 条 holdout 的 UTF-8 byte 5-gram cosine 最大值 `<0.75`；
- secret/credential/private key/holdout reference answer：0；
- RWKV-PEFT tokenizer 后所有训练 target 均完整位于 `ctx_len=2496` 内；不允许 target 被截断。

## 训练、部署与复测

- SSH：本机 alias `rwkv-8222`。
- 训练工程：`/home/chase/chase/RWKV-PEFT`。
- 上传目录：`/home/chase/chase/RWKV-PEFT/data/rwkv_lh_action_state_tuning_round1_2k_v1/`。
- 基座：`rwkv7-g1i-13.3b-20260805-ctx16384.pth`，61 层，embedding 4096。
- 固定训练参数：`--peft state --op fla --data_type jsonl --loss_mask qa`，bf16，单 GPU，
  `ctx_len=2496`；学习率与 checkpoint 间隔在训练启动前另行冻结，不以结果倒推。
- GPU：固定 GPU0。训练启动前可停止该账号在 GPU0 上的现有推理服务；本轮优先级最高。
- 部署：vLLM-RWKV，以 `VLLM_RWKV7_INITIAL_STATE_PATH` 加载选中 state checkpoint，在 GPU0
  重新部署。原始基线结果必须在停止前固化；需要 A/B 时以串行切换服务完成，不占用 GPU3。
- 复测顺序：数据来源缺陷 canary → ECRA route canary → 全部登记历史缺陷 → route120/E2E90
  全量（前置门通过后）。结果按同一冻结 verifier 与协议比较。
