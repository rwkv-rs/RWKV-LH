# S67 zero-state cascade head 预注册

## 已冻结证据

- S67 cases SHA-256：`0401966e7633c77cb3950019857324f23a625cc9a290b13c80804001400fd859`。
- S67 feature manifest SHA-256：`6bc00c202765b6621370e618a7a66244c52232b1e5027c29c86e78ae78d2b64c`；只包含 train/dev，locked-test 在 JSON 解析前跳过。
- 当前 S66-M1 head SHA-256：`858982e45822b975c3c4cf0badf4a89c12b2c85a76e7157da85809a246b7c304`。
- S66 在 S67 dev 的 frozen baseline result SHA-256：`25cd4e8e979eb4f6373c594eb5e46f9f77ca1c9cacaca2540f8ac49deb3881ea`；accuracy `0.124`、macro-F1 `0.07324326846981309`、minimum recall `0.0`。
- S60/S61/S65 数据、特征与现有门槛沿用各自冻结 manifest，不修改评价算法或阈值。

## 固定结构

- 每次请求仍只做一次 2.9B RWKV hidden 提取，feature 固定为 `concat(mean,last)`，不采样、不生成文本。
- frozen baseline expert 为完整 S66-M1，保留其内部 S60/S62 Soft-MoE 与原 normalization。
- 新 V2 expert 为 fresh `Linear(5120,h) -> GELU(tanh approximation) -> LayerNorm -> Dropout(0.05) -> Linear(h,25)`，只用 S67 的 2000 train 优化。
- learned gate 为 `Linear(5120,g) -> GELU -> LayerNorm -> Dropout(0.05) -> Linear(g,1)`。
- 唯一 raw-logit 公式为 `S66_logits + sigmoid(gate_logit) * (V2_logits - S66_logits)`；没有规则 gate、mask、阈值路由或 argmax 后处理。
- V2 expert 与 gate 使用且只使用 S67-train 的 feature mean/std；S66 expert 保持自己的冻结 normalization。

## 固定候选与优化

共同参数：seed `1067`；AdamW；weight decay `1e-4`；batch `256`；gradient clip `1.0`；deterministic cuBLAS；物理 GPU0。

1. `S67-C1`：V2 expert h64，gate h64；gate domain-BCE/MSE/margin 权重 `1.0/0.25/2.0`。
2. `S67-C2`：V2 expert h128，gate h64；gate domain-BCE/MSE/margin 权重 `2.0/0.5/5.0`。
3. `S67-C3`：V2 expert h256，gate h128；gate domain-BCE/MSE/margin 权重 `5.0/1.0/10.0`。

V2 expert：learning rate `1e-3`，cosine schedule，最多 `160` epochs，patience `30`；S67 train 每类等权。Expert checkpoint 固定按 `min(accuracy/0.96, macro-F1/0.96, minimum-recall/0.90)`、accuracy、macro-F1、较早 epoch 的字典序选择。Gate：learning rate `3e-4`，cosine schedule，最多 `120` epochs；S67/S65 train 两域质量各半、域内类别等权。S67 的 domain target 为 1，S65 为 0；gate loss 为 blended-label CE + 候选权重乘 domain BCE + S65 frozen-baseline MSE + S65 baseline-correct capped-margin preservation（cap `4.0`）。

每个候选先冻结自己的 V2 expert checkpoint，再训练 gate。候选、epoch、权重和评价口径在运行后不得改变。

## Dev 门与选择

- S67：accuracy `>=0.96`、macro-F1 `>=0.96`、每个有支持类别 recall `>=0.90`。
- S65 与 S61：overall accuracy `>=0.96`、focus accuracy `>=0.95`、continuation/final boundary `>=0.97`、focus 最低有支持类别 recall `>=0.90`。
- S60：S28 accuracy/macro-F1 `>=0.99`；S39/S52/S53 `>=0.96`；S55 accuracy/macro-F1 `>=0.98` 且最低 recall `>=0.90`。
- S60、S61、S65 各自相对 frozen S66 baseline 的 baseline-correct regression 必须全部为 `0`，每个 S60 source accuracy 不得下降。
- S67 相对 S66 baseline 必须有正 net rescue；raw logits、hidden 和 RWKV 输出不得被修改，采样与文本生成计数必须为 0。

每个 gate 取最早满足全部门的 checkpoint；若始终不满足，仅按“通过门数量、所有连续门的最低归一化比率、S67 accuracy、较早 epoch”保留一个诊断 checkpoint，且该 checkpoint 不具备资格。候选选择顺序固定为 `C1 -> C2 -> C3`；只有前序候选未通过才允许选择后序候选。若全部失败，zero-state 不具备资格，转入同一 S67 2000 train 的编号 state tuning；不得通过修改门槛、规则 mask 或用 locked-test 选模补救。

## Locked-test 与产品变更

- 在唯一 dev 候选及其 artifact SHA-256 冻结前，禁止解析 S67/S65 locked-test 或访问标签。
- dev 通过后才实现/验证 cascade artifact 的本地服务加载；先离线一致性测试，再开独立实验端口做真实 Harness canary。
- canary 通过前不替换产品 S66，不停止产品隧道，不修改或删除任何 RWKV 原始输出。
