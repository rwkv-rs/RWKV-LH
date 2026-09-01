# G1J 2.9B S60 Selector Head 适配 R2 预注册

- 登记时间：2026-09-01，早于任何 G1J 2.9B Hidden 特征提取或模型推理。
- 原因：冻结 S60 Head 与 G1J artifact 的 portable identity 不一致，严格 weight-swap 在服务启动阶段正确失败。
- 边界：这是必要的 Selector 分类 Head 适配，不是 13.3B State Tuning，也不改变 Strong Planner、13.3B Executor、Goal Audit 或 Harness 判定。

## 冻结输入与模型

- dataset：`data/datasets/rwkv_lh_network_selector_requirement_byte_tail_s60_v1/cases.jsonl`
- cases SHA-256：`3b60bf7fd69a2d085480ffcac4b31eca0655e38a3a67bf2f308660f629ea3faf`
- manifest SHA-256：`16d05f9a7e4e5c94f3f314ec5848384b96b95045609fde25d92cfb3d497be76f`
- split：train `13,143`；dev `2,571`；locked test `2,579`。
- G1J source PTH SHA-256：`966f3420f833532aae3fb1fd6326533b08d43d23b7b03eaa2f0694a30b64a239`。
- G1J vLLM artifact `model.safetensors` SHA-256：`c1a316e75abd50f5edc3358fbb2c7d1cb18c611d9b2aa5b888091c8d45cc866c`。
- engine revision：`67f0c5996c50dca0ad779da545cb491527de988f`；zero State；WKV `fp16`；batch `1`。
- 输入协议保持 `rwkv-lh.exact-tool-selector-input.v7-requirement-byte-tail`；运行时 Strong frontier 复用已冻结的 `CurrentDirectStageV3` 外壳，不引入新阶段格式。

## 冻结适配配方

1. 只读取 train/dev，按原 S60 persistent trajectory 顺序重放；每个 prefix 同一 forward 提取 Hidden `concat(mean,last)`，特征维度 `5120`，不生成文本、不 sampling。
2. fresh Xavier h64 MLP；seed `1059`；dropout `0.05`；AdamW `lr=0.001`、weight decay `0.0001`；batch `128`；cosine；最多 `160` epoch；patience `30`；gradient norm `1.0`；每个 `(source,label)` 相同总权重。
3. dev 选定前不得解析 test JSON；只有全部 dev 门通过后才允许一次性提取 locked-test 特征并评价。
4. Head portable identity 必须绑定 G1J artifact SHA、zero State、V7 input、engine revision 与新 feature manifest；不得复制或改写旧 G1I 身份。

## 固定门槛

- S28 accuracy/macro-F1 `>=0.99`。
- S39/S52 accuracy/macro-F1 `>=0.96`。
- S53 accuracy/supported-macro-F1 `>=0.96`。
- S55 accuracy/supported-macro-F1 `>=0.98`，每个支持类 recall `>=0.90`。
- locked test 使用同一门槛；portable raw-logit replay argmax 必须完全一致，最大绝对差 `<=0.005`。
- 不得在结果后修改阈值、标签、split、相似度算法、logit 后处理或重选规则。

## 后续 Goal Loop 测试

只有 Selector dev + locked test 全部通过后，才启动 G1J Selector 服务，并使用原预注册的三例 Agent Ladder、concurrency `1`、max transitions `300`、progressive disclosure、Selector Top-K `3`。该阶段结果标记为 `G1J-compatible-head R2`，不冒充严格 weight-swap。
