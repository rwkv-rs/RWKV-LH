# 13.3B zero-State Executor-Args 协议冒烟结果

日期：2026-09-04（Asia/Shanghai）

## 有效结论

R3 native zero-State：`4/4` 通过固定门槛。

- operation 分别固定为 `list_directory`、`read_file`、`write_file`、`run_command`；四次首次生成都保持上游选定 operation。
- 四次 raw output 均为模型侧 `name/arguments` 结构；当前 parser 全部转换为 canonical `function/params`。
- 四次均通过 Executor-Args parser 与 Harness 参数规范化；缺省字段只由注册表默认值补齐，`controller_semantic_fields_generated=false`。
- 四条 decision 均为 `accepted=true`、`transport=native_rwkv`、模型 `rwkv7-g1j-13.3b-zero-state-capability-ctx16384`。
- 运行未执行工具、未加载或选择 StateTune，也不评价 Selector。

这说明在每个 action 干净启动、工具已正确选定的条件下，当前 13.3B zero-State 能稳定完成这四类参数填写；旧 trace 的 12 次连续 action 协议失败不能归因于“13.3B 完全不会输出工具格式”。该结论只覆盖四例冒烟，不能外推为完整 Executor 数据集通过。

## 无效轮次保留

- R1：模型输出 `4/4`，但 runner 误用 `prompt_replay`，不进入产品 native 指标；原始文件 `RESULT.json`。
- R2：四条 decision 实际全部 accepted/native，但 runner 把 transport 常量错写为 `native_rwkv_state`，机械记为 `0/4`；原始文件 `R2_RESULT.json`。
- R3：修正为源码定义的 `native_rwkv`，其余条件不变；有效文件 `R3_RESULT.json`。

## 摘要

- `PREREGISTRATION.md` SHA-256：`40e39a4b4f226e0fc2399714fe4b92c0ead464436db41d1f99450a8773c60fea`
- R1 SHA-256：`3fca22a8e3378e86f83c3fcb6ec3e1c36f898e7b4721eaf6371a65b39a32923d`
- R2 SHA-256：`dc03bdf732a380c9810b05fcf02f154aeecbcc33a2bb354dfdc2d1fcefb778f9`
- R3 SHA-256：`0b046dbd47b0e1c9fc1e5796d9d905cb9706797763d6b2a9e7ee1600f454113d`
- runner SHA-256（R3）：`766a86b7e687586b088b775d2a3c61d4cbb36f721e123abe1f922c6794ef914f`
