# RWKV-LH evaluation dataset v1

此目录保存架构消融和全量回归使用的版本化数据集副本。数据由
`temp/analyze_rwkv_lh_architecture_history.py` 从仓库内的权威 benchmark
资源导入；`manifest.json` 在导入时记录源路径、SHA-256、字节数、用途和目标文件。

预期内容：

- `core30.tasks.json` 与 `core30.acceptance.json`：基础、中等、困难共 30 题。
- `lh12.tasks.json` 与 `lh12.acceptance.json`：长程压力 12 题。
- `lh_control_30.tasks.json`：确定性架构回归 30 题。

消融实验使用前必须校验 manifest 中的源文件和目标文件摘要一致。不得在不同方案间
更换题目、验收条件或评价参数。
