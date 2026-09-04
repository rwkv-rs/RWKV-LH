# Round118 v17 Full90 全局诊断协议

## 目的

Round118 v17 Basic30 的 Stage A 结果为 Strict `21/30`，未达到原预登记的晋级门槛。
但是只停留在 Basic30 会形成局部分析陷阱，无法检查 Medium/Hard 中的长依赖、集合、恢复、
多文件协调和上下文 rollover。根据用户明确要求，本协议在不改变任何运行时代码、数据、
采样或评价口径的前提下，追加一次完整 90 题诊断。

本轮是 **全局诊断实验**，不是原 Stage A 的 confirmatory，也不能因为某一子集改善而宣称
v17 已通过。Basic30 失败结论继续保留。

## 冻结对象

- 源码与数据：`data/experiments/Round118_v17_source_manifest.json` 登记的 47 个文件；
  运行前后必须 `47/47` hash 匹配。
- 模型：`rwkv7-g1i-13.3b-20260805-ctx16384`。
- endpoint：`http://127.0.0.1:29610/v1`。
- 数据集：`rwkv_e2e_90_v1`，按 runner canonical order 执行 B01–B30、M01–M30、H01–H30。
- sampling：temperature `0.05`、top-p `1.0`、top-k `0`，其余使用冻结 runtime 设置。
- `max-transitions=200`，concurrency `1`，WSL `UbuntuRecovered`，uv `0.12.5`。
- 运行目录：`data/experiments/Round118_v17_full90_diagnostic`。

## 不变量

1. 90 题全部重新运行；不复用或拼接先前 Basic30 结果。
2. 运行中不修改 runtime、prompt、工具 schema、数据、外部验收、相似度或阈值。
3. Controller 不读取隐藏验收来选择工具、修改参数、修改产物、否决或改写 RWKV Final。
4. 所有 Final 必须保留 raw RWKV 文本；失败、blocked 或预算耗尽也必须产生用户可见输出。
5. 只允许已登记的简单 wire normalization 与“已选 operation 的精确 schema 反馈”。
6. 中途即使指标已不可能超过历史最佳，也继续完成 90 题，以保留全局缺陷分布。

## 诊断指标

- 全量及 Basic/Medium/Hard 分组的 Strict、External、Agent completed、FP、FN。
- requests、Actions、protocol rejections、prompt tokens、rollovers。
- Final 非空/raw equality、Action terminal/result 完整性、causal event reload/digest 完整性。
- 固定 external artifact checks 的 `utf8-byte-ngram-cosine.v1` missing-zero similarity。
- 与 Round46 Full90 最佳基线和 Round101 退化基线逐题比较。
- 每题人工标记：首次 RWKV 偏离、接口/环境影响、Observation 后放大、恢复/rollover 放大、
  Final 与最后事实是否一致。

## 完成判断

本实验不设置提前停止门槛。90 题完成后才形成结论。任何架构建议必须同时解释 Basic、
Medium、Hard 的共同原因与差异，不能针对单题或单难度增加特判。
