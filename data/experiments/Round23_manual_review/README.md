# Round23 人工逐题因果审阅

## 边界

- 来源版本：Round23 冻结公共轨迹，公共 manifest SHA256 为
  `a59225f93a07beac1355ce3ac05a035d67fb6123d0bfe7d95e63663d7b562adf`；对照版本为 Round22。
- 用途：逐题追溯最早偏离和后续放大环节，再由全 90 题共同决定下一轮结构，不预设功能方向。
- 生成方式：`temp/build_round23_blind_fact_index.py` 只生成事实定位索引；所有因果判断由人工回读每题
  `model_trace.json`、`event_log.json`、`state_timeline.json`、`audit.run_state` 和最终 workspace 后填写。
- 盲审边界：标准答案接入前不解析 `results.json` 内容、acceptance、reference answer、Codex answer，也不读取
  audit 中的 external/score 字段。人工可以依据用户可见请求、实际 source 和实际产物判断显式关系。
- 标记：`observed` 表示轨迹直接证明；`inference` 表示跨事件推断；未验证反事实不得写成结论。

## 产物

- `../Round23/blind_lifecycle_fact_index.json`：90 题事实定位索引，不含自动根因分类。
- `BASIC_B01_B30_PRESTANDARD_CAUSAL_REVIEW.md`：Basic 30 题逐题盲审。
- `MEDIUM_M01_M30_PRESTANDARD_CAUSAL_REVIEW.md`：Medium 30 题逐题盲审。
- `HARD_H01_H18_PRESTANDARD_CAUSAL_REVIEW.md`：Hard H01–H18 逐题盲审。
- `LONG_HORIZON_LH01_LH12_PRESTANDARD_CAUSAL_REVIEW.md`：Long-Horizon LH01–LH12 逐题盲审。
- `PRESTANDARD_REVIEW_MANIFEST.json`：以上 90 题盲审与公共源数据的冻结摘要、边界和 SHA256。
- `CODEX_REFERENCE_ANSWERS_PREACCEPTANCE.md`：仅从题面、公共输入和公开 generator 独立完成的 90 题参考答案。
- `REFERENCE_ANSWER_MANIFEST.json`：独立参考答案及其公共来源的冻结 SHA256；后续 acceptance 差异不得回写答案。
- `REFERENCE_VS_ACCEPTANCE_DIFFERENCES.md`：独立答案与acceptance的11项差异，区分答案错误、歧义和评价收窄。
- `*_POSTSTANDARD_COMPARISON.md`：Basic 30、Medium 30、Hard 18、Long-Horizon 12逐题标准答案后复核。
- `POSTSTANDARD_COMPARISON_MANIFEST.json`：90题复核、acceptance与Round22/23结果的冻结SHA256和计数。
- `CROSS_90_CAUSAL_SYNTHESIS.md`：连接90题最早断点、后续放大环节、源码落点与分轮整改顺序；不回写冻结逐题结论。
- 后续跨题结构合成不得回写上述冻结审阅文件。
