# Stage7 预注册：Factory 语义扩展与成对状态差分

日期：2026-08-27（seed、Factory 扩展、训练和候选评测前）

## 动机与因果假设

Stage4 在冻结 ECRA route120 B 上达到 first-tool 100/120，并保持 local network FP=0，
但 failed/interrupted 为 9/120；Stage5 把 failed/interrupted 降至 1/120，却把
`final_answer`/下游动作扩散到 evidence-missing 状态，mixed 从 17/20 降至 3/20；Stage6
恢复 mixed 到 14/20 后，public-web/connector 又降至 16/25、8/20。自身 synthetic dev 明显
高于冻结集，证明继续复制既有模板不是合格修复。

本轮只检验两个因果假设：

1. 同一 immutable request、同一语义实体、只改变已提交 evidence/remaining obligations 的成对
   selector 状态，可以学习“缺证据继续、证据足才结束”，而不把 completion 正例泄漏到初始态；
2. 同一领域实体、只改变“普通公开网页内容”与“连接器中的结构化记录字段”的成对自然请求，
   可以学习 source role，而不是记忆 operation/query 表面词。

## 数据所有权与 Factory 边界

- `RWKV-state-factory` 只用强模型扩展公开请求的表面语义、虚构实体和领域；它不产生
  operation、参数、状态标签、Controller event、Gate 结果或 final label。
- RWKV-LH 读取 Factory 的公开 surface card，由本地确定性 oracle 填充虚构 fixture，并通过当前
  ActionHarness、Network Gate、Controller 和 progressive G1i renderer 真实回放。
- 只有 replay、target parse、literal binding、completion boundary 和污染检查全部通过的 stage
  才进入正向 SFT。强模型输出失败只进入拒绝记录，不作为训练正样本。
- ECRA120、E2E90 的 request、答案、URL、实体、目标文件和 trace 不进入 Factory prompt 或训练数据。

## 冻结规模与配额

Factory 先生成 train/dev family-disjoint 的 500 个 surface family：每个 family 机械渲染 4 个
成对 selector state，共 1,600 train + 400 dev。训练另加入 Stage1 的 400 条 selector safety
anchor，最终严格为 2,000 train / 400 dev。

| cluster | train family / stage | dev family / stage | 学习目标 |
|---|---:|---:|---|
| phase evidence contrast | 100 / 400 | 25 / 100 | 同请求 pre-evidence 工具 vs post-evidence final |
| ordinary web vs connector | 100 / 400 | 25 / 100 | 同领域 source-role 最小差分 |
| mixed/privacy local-first | 100 / 400 | 25 / 100 | 初始本地依赖、观察后联网或 Gate 拒绝 |
| no-progress/success stop | 100 / 400 | 25 / 100 | provider unavailable、成功观察后的校准停止 |
| Stage1 safety anchors | — / 400 | — / 0 | 保留 selector schema、local/deterministic 与完成边界 |
| **合计** | **400 / 2,000** | **100 / 400** | |

同 family 的四条数据必须组成显式 contrast group；不得以无关 padding 制造唯一性。train/dev
semantic family overlap=0，所有最终 `text` exact duplicate=0。

## 数据门禁

1. Factory surface schema、placeholder、禁用工具名、虚构实体和跨 family 去重：100%；
2. Controller/Harness replay、target parse、literal/state binding：100%；
3. privacy backend execution=0；provider unavailable 不得生成伪造事实型 final；
4. 每个 contrast group 的 state delta 只允许出现在预登记字段；
5. 与冻结 210 条 holdout exact overlap=0，UTF-8 byte 5-gram cosine 严格 `<0.75`；
6. secret、credential、private key、真实评测答案和真实用户数据命中=0；
7. RWKV-PEFT 权威 tokenizer 下 target 100% 完整位于 ctx_len=2496；
8. manifest 记录 seed、Factory 代码、模型名、请求参数、raw completion、拒绝原因、文件摘要和
   生成命令；不记录 API key。

## 训练协议

- SSH：`rwkv-8222`；项目：`/home/chase/chase/RWKV-PEFT`；GPU 固定 0；
- 基座：`rwkv7-g1i-13.3b-20260805-ctx16384.pth`；
- 实验 parent：Stage4 step1140，SHA-256
  `8af6f29bb8cd68ed2f5e7ca6bcee56f7df7c53bccb083a80d1fa51e680d81960`；它只作为实验续训起点，
  在通过本协议全部门禁前不得替代正式 Stage1；
- `--peft state --op fla --data_type jsonl --loss_mask target_suffix`，bf16，ctx2496，BOS0，
  micro batch1，gradient accumulation1，seed833；
- 数据按 contrast group 固定散列交错，不能把 completion 集中在单一区间；
- 1 epoch / 2,000 steps，LR `3e-6 -> 6e-7` cosine，warmup20，每 500 step 保存；
- 预登记候选为 step500/1000/1500/2000。先做 checkpoint/tokenizer/state-orientation 校验，再按
  同一冻结 evaluator 评价，不根据单题改 parser、模板或阈值。

## 固定验收与部署选择

每个 checkpoint 依次运行：本轮 dev400、Round1 dev200、ECRA route120 B、Stage1 Shadow 固定
canary（仅旁路分类观测，不计主 state 得分）、工程测试和 E2E90 catalog validation。候选硬门：

1. Round1 dev200 schema/operation=200/200，direct arguments exact `>=107/121`；
2. ECRA local-only `>=26/30`、deterministic `>=15/15`；
3. public-web `>=23/25`、connector `>=12/20`、mixed `>=17/20`、privacy `>=9/10`；
4. network macro-F1 `>=0.974`、local network FP=0、required-online FNR `<=0.0924`；
5. failed/interrupted `<=4/120`，privacy backend execution=0、rejection coverage=1.0；
6. 本轮 dev400 每 cluster `>=0.95`，成对 contrast consistency `>=0.95`；
7. checkpoint 全 finite/nonzero、tokenizer/BOS/target-suffix 与 vLLM direct `[V,K]` orientation
   全通过，工程回归无新增失败。

在通过全部硬门的候选中，选择顺序冻结为：先最早达到硬门的 checkpoint；若同一步存在多个训练
臂，则按 `min(web, connector, mixed, privacy)`、stop fail、first-tool total、与 Stage4 cosine
依次比较。没有候选通过时恢复并保留 Stage1 step500，不能降低门槛，也不能部署 Stage4。

只有 route/dev 门通过才运行 RWKV-only E2E90 与完整 contract-graph E2E90。强模型 transport
availability 单独报告；外部 403/5xx 不计作 RWKV 行为改善或回归。
