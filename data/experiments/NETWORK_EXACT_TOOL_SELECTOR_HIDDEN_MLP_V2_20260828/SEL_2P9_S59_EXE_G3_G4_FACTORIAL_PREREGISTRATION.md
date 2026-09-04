# S59 × G3/G4 真实 Harness 固定因子消融预注册

日期：2026-08-29

## 目的

在当前“双模型、双 lane、独立 state”架构内，量化 Selector 输入布局与 Executor state 的主效应及联动，不用局部用例替代真实 Harness。Selector 只读取工具名称、描述与有界进度，输出未修改的 25 类 raw logits argmax；Executor 只接收已经提交的单个工具契约和当前执行问题。任何 RWKV 原始输出均不得重写、删除、重排、隐藏或由控制器语义替换。

## 固定输入与实现

- Selector 模型：RWKV7 G1i 2.9B，权重 SHA-256 `01f39dd59fc402fbe8ba49765a1997ee9dbc82427bf0ece6a4fac520e9eb8044`，物理 GPU0。
- Selector state：zero，SHA-256 为 64 个 `0`；本实验不加载 Selector tuned state。
- S53：V4 request-last Head，文件 SHA-256 `fa25b05e69d484e677d96abe270161ce240449217f39ad81367fc27b6e284fd2`，仅作为旧布局对照。
- S59：V6 current-question-last Head，文件 SHA-256 `9404cf0905a897106b77a1f6c33e8a11c6262d7c9c64c64d284e7af7209a379c`，Head hash `0a1de84c66f47351786dc10b0552b6bc68e8ec0923f1ad4c8b44ec6c2250c534`。
- Executor 模型：RWKV7 G1i 13.3B，基础权重 SHA-256 `5d97772ba04a81bdaeba90e1d6d306c70560bf4f784522be61cdcade69e30562`，远端物理 GPU0。
- G3：已冻结的 `EXE-G3-MULTISTAGE` 最早通过 checkpoint step 2000，state SHA-256 `13f6586951666962405286dda8e45c1eae82a37c68c21b3b75dbbb04c6e54f12`。
- G4：只读取 `run_exe_g4_true_workflow_joint_ablation_r2_metadata_complete/ABLATION_RESULT.json` 中按既定规则选出的最早通过 checkpoint；若没有通过候选，G4 两个真实 Harness arm 记为不可运行且不得自行放宽门禁。
- 真实 Harness 固定集：`E2E-B01,E2E-B02,E2E-B10,E2E-M03,E2E-M12,E2E-H10`。
- 统一参数：`supervisor=none`、`tool-disclosure-mode=progressive`、`independent-selector=true`、`concurrency=3`、`max-transitions=200`、Executor temperature `0.1`、top-p `1.0`、top-k `0`、请求重试 `1`。
- 统一完整性算法：`temp/validate_current_architecture_e2e_run_20260829.py`，SHA-256 `a90ce79aab81c36767edd7770969c5c4a046f610f04b9f112eaf82f1312d7aaf`；每个 Executor 生成输入必须在续写点前以 `current_requirement` 或显式 `current_question` 收尾，且完整用户要求在 transcript 中恰好一次。S59 的每一个 Selector checkpoint 还必须满足 V6 顶层最后字段为 `current_question`、嵌套最后字段为 `question`。
- 固定 live2 验证器：`temp/run_current_architecture_live_network_e2e_v2_20260829.py`，SHA-256 `4472eeb6bd7f45b00c1a25ba3debe3fb0b545afa191e2c7a41344b92e8f211c5`。
- 已选组合的联网与检索质量仍使用固定 live2、retrieval9 和 Full90 数据、阈值与验证器；不得在看到结果后修改口径。

## 固定 2 × 2 arm

四个 arm 全部运行，不因先出现通过结果而提前停止：

1. S53 + G3：旧 Selector 布局、现有 Executor state。
2. S59 + G3：问题末置 Selector 布局、现有 Executor state。
3. S53 + G4：旧 Selector 布局、真实工作流 Executor state。
4. S59 + G4：问题末置 Selector 布局、真实工作流 Executor state。

每个 arm 记录：严格通过数、失败 case、生成输入数、问题末置输入数、原始生成数、25 类 logits 完整性、输出非干预完整性、Selector/Executor 模型与 state attestation。

主效应使用固定差分计算：

- Selector 主效应：`mean(pass(S59,G3), pass(S59,G4)) - mean(pass(S53,G3), pass(S53,G4))`。
- Executor 主效应：`mean(pass(S53,G4), pass(S59,G4)) - mean(pass(S53,G3), pass(S59,G3))`。
- 联动：`pass(S59,G4) - pass(S59,G3) - pass(S53,G4) + pass(S53,G3)`。

以上均以 6 个 case 的严格通过数计算，不改用主观评分。

## 固定门禁与选择规则

arm 通过需同时满足：6/6 严格通过、完整性状态 `valid`、生成输入数等于原始生成数、每次生成在续写点前有已登记的当前问题字段、Selector 保留全部 25 logits 且 `postprocessed=false`、RWKV 原始输出修改或删除数为 0。

部署选择只允许问题末置的 S59：

1. 若 S59+G3 通过，选择 S59+G3；这是 state 数量最少且先验成本最低的组合。
2. 否则若 S59+G4 通过，选择 S59+G4。
3. 否则不发布，不以 S53 对照替代用户确认的输入协议。

通过 canary 后，所选组合还必须依次满足：live-network 2/2、retrieval-quality 9/9 全部硬门禁、Full90 全部 90 个任务被调度且完整性有效；Full90 只允许已登记的 `E2E-LH09/mock_api` 能力边界，不允许其他 runner failure。

## 输出保全

所有运行目录只新建不覆盖。HTTP response envelope、raw token ids、raw logits、服务日志、state attestation、审计 journal、结果与失败均保留。解析、评分和控制器拒绝发生在原始输出持久化之后；不得通过重试、后处理或测试特判改善分数。
