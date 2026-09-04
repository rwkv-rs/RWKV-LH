# Round146：Path Literal Integrity Canary 分析

## 结论

Round146 为 `2/3`。B04、LH06 pass，路径完整性与 head-noun/不可信载荷规则同时有效；M16 因 dependency handoff 丢失精确 action observations 而失败。

- M16 的 05 scout 真实 `read_file` 输出为 `{"id":"05","value":13}`。
- 03/04 scout 的 RWKV Final summary 越出自己的 atom scope，臆造了一份全量结果，其中 05=8。
- v3 为压缩输入删掉了 dependency action outputs，只把 candidate summary 与 artifact hashes传给下游；writer无法从 hash恢复值，采纳了错误 summary，写出 05=8。
- finalizer只检查 shape/coverage，没有重新读取源文件，因此错误被接受。

原始记录：`data/experiments/Round146_path_literal_integrity_canary_B04_M16_LH06_20260822/`

## 整改

compact dependency handoff 恢复最多8条精确 action observations（operation、最小路径参数、success、bounded output、error），移除自然语言 candidate summary。完整 trace仍只在审计层；模型层只接收小型事实投影。下游明确以 observations 为唯一依赖事实，不能从 atom Final summary 推断值。

