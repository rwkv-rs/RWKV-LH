# SEL-2.9B-S52 request-last 成对消融预注册

日期：2026-08-29（Asia/Shanghai）

## 目的与不可变边界

验证 RWKV 输入的统一排列：固定契约、菜单、状态和已观察证据在前，当前任务或当前阶段问题作为最后一个闭合字段，紧邻续写点。Selector 仍只负责从 25 个工具的名称和描述中分类；它不接收参数 schema、不生成文本，也不承担用法和参数生成。Executor 仍为独立的 13.3B RWKV，并使用自己的 state。

不得检查后改写、删除、重排、隐藏或诱导 RWKV 原始输出。Selector 保存完整原始 logits；Executor 保存逐字节原始生成。控制器只做协议校验、原始 argmax 和确定性执行。

## 成对实验臂

- A：S51/V3，对照。`task_request` 位于 bootstrap 尾部，但每一步的 `stage_objective` 不是最后一个字段。
- B：S52/V4-request-last，候选。除渲染版本和派生 ID/哈希外，与 S51 的 2421 条前缀逐条同源、同标签、同 split；每一步 `stage_objective` 必须是 JSON 最后字段。

S52 生成前不得读取任何模型指标。S51 已完成的 V3 特征只作为冻结对照，不得覆盖。

## 冻结来源

- S51 cases：`da7d280db64728b1b77f2db24cd0ae86b2735f3e130d0e6597897bffcaec242f`
- S51 manifest：`7b9ac06887d942ed10e98d8825648160ce970a7257fdf1d05acaa07df4f2aacb`
- S51 feature manifest：`c64dc35990efd019fc4702d9dad0c70b96e47e3b59c8be1e5d18f00fcd6cbafa`
- S28 cases：`a993900649ae0943053df141d03c0e615b297864083f7893b49ae83391b98922`
- S28 feature manifest：`a048d5cd580fc50b4af525b0f6a9c90ad44120ce6d81b56e7a981970e10548ef`
- S39 cases：`b85ff487cd0902743ede4299c651f3af4a5fa92f0a1240edb3e89b68b7ac0dab`
- S39 feature manifest：`b56e5cefab701128f7217bdecb00f2c1bd64b9505b8be61d9e55a1fc78c13481`
- 2.9B 权重：`01f39dd59fc402fbe8ba49765a1997ee9dbc82427bf0ece6a4fac520e9eb8044`
- vllm-rwkv revision：`67f0c5996c50dca0ad779da545cb491527de988f`
- V4 renderer：`03e9068e1875ab91fd2b6aae51c2a3e02642a6988e58c5fc76bf438ee17db23f`

## 固定数据与隔离

- S52 必须有 634 条 trajectory、2421 条 prefix；train/dev/test prefix 为 1615/399/407，trajectory 为 423/105/106。
- 每条 S52 必须与对应 S51 保持 `selector_input`、label、split、language、position、source kind/source ID 完全一致。
- test 行在 Head 训练与 dev 选择阶段必须在 JSON 解析 label 前跳过；test feature 不得进入归一化、训练、温度选择或候选选择。
- 固定历史 canary：`E2E-B01,E2E-B02,E2E-B10,E2E-M03,E2E-H10,E2E-M12`，仅在 Head 锁定后使用。

## 固定特征与训练

- 物理 GPU0；`CUDA_VISIBLE_DEVICES=0`。
- 2.9B RWKV、零 state、batch size 1、持久 trajectory replay。
- 每个 prefix 只做一次前向，同时取得 mean hidden 与 last hidden；融合顺序固定为 `[mean,last]`，维度 5120。
- 不调用 sampling，不生成 RWKV 文本。
- A 与 B 分别训练独立 Head；共同加入 S28、S39 作为冻结 retention 源。
- loss 权重为每个 `(dataset source,class)` 等总质量。
- seed 1052；dropout 0.15；epoch 上限 80；batch 128；AdamW；lr `8e-4`；weight decay `1e-3`；patience 12；确定性算法与 `CUBLAS_WORKSPACE_CONFIG=:4096:8`。
- 候选容量顺序固定为 hidden 64、hidden 128；选择首个通过全部 dev gate 的候选。
- checkpoint 排序键固定为：natural dev macro-F1、natural dev accuracy、S39 macro-F1、S39 accuracy、S28 macro-F1、S28 accuracy、负三源 dev loss 总和。

## 固定指标和阈值

分类相似度定义为 canonical operation exact equality：相同为 1，不同为 0；同时报告 accuracy、macro-F1、逐类 recall 和混淆矩阵。不得在运行后改变口径。

Dev gate：

- natural（S51 或 S52）accuracy 与 macro-F1 均不低于 0.96；history/current 均不低于 0.95；有支持的每类 recall 不低于 0.90。
- S39 accuracy 与 macro-F1 均不低于 0.96；history/current 均不低于 0.96；有支持的每类 recall 不低于 0.90。
- S28 retention accuracy 与 macro-F1 均不低于 0.99。
- portable artifact replay argmax 完全一致，最大 logit 误差不高于 0.005。

锁定 test gate：

- 三个数据源各自采用相同阈值；natural 历史 canary 的完整 route prefix exact accuracy 不低于 0.96。
- 锁测前 Head 文件 SHA-256 与内部 `head_hash` 必须固定；测试后不得重训或换阈值。

真实 Harness gate：

- 固定 canary6 必须 6/6 strict pass；固定 live-network2 必须 2/2 strict pass。
- Full90 必须跑完全部 90 例并报告；结构不支持的工具必须显式失败，不得补测试专用工具或特判。
- 联网质量继续使用已经冻结的 9 例 retrieval 指标；必须维持全部质量 gate，不得以路由成功替代检索质量。

## 选择规则

B 只有在自身所有离线 gate、canary6、live2 和检索质量 gate 均通过，且相对 A 没有新的同类回归时才可成为本地第一版。若 A/B 都未通过，不部署；如 B 通过但 Full90 仍有一般能力缺陷，允许作为明确标注范围的联网第一版，但不得宣称完成真实 Harness。

所有输出、哈希、失败样本、原始 logits、原始生成和全流程记录写入本实验目录；不根据结果修改本预注册。
