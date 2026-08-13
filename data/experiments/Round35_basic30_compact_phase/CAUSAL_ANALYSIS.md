# Round35 Basic30 阶段紧凑 capsule 因果分析

## 结果与 Round33 对比

| 指标 | Round33 | Round35 |
|---|---:|---:|
| Strict | 5/30 | 10/30 |
| External | 21/30 | 20/30 |
| Agent completed | 7/30 | 12/30 |
| FP | 2 | 2 |
| FN | 16 | 10 |
| 模型请求 | 472 | 383 |
| Task | 160 | 128 |
| Attempt | 116 | 110 |
| model contract error | 118 | 18 |
| action argument rejection | 16 | 14 |

阶段隔离把 contract error 从 118 降到 18，请求与 Task 数同步下降，Strict 翻倍。External 没有提高，说明主要收益是减少流程放大与假阴性，还没有普遍提高 RWKV 生成内容的正确率。

## 逐题最早错误

| Case | Round35 结果 | 最早错误与放大链 |
|---|---|---|
| B01 | External PASS / blocked | 正确写入后，验证读取输出 `tool+args`；项目只接入 `tool+arguments`，纯格式阻塞 |
| B02 | External PASS / blocked | 正确 report 后，冗余 verify Task 同样输出 `tool+args` |
| B03 | Strict PASS | 读取、更新、读取验证均完成 |
| B04 | External FAIL / blocked | 目录任务错误使用 write_file 创建路径，后续 copy/recovery 参数失败 |
| B05 | External PASS / blocked | 正确删除后重复读取/验证，最后局部 Task 判断拒绝 |
| B06 | Strict PASS | Round33 的 `model_action/source_label` 复制链消失 |
| B07 | Strict PASS | 两步链完成 |
| B08 | External FAIL / blocked | RWKV 幻觉 SHA256 并写入 manifest；后续冗余 write_json 又混入 write_file 参数 |
| B09 | Strict PASS | 内容正确，虽仍有重复写入/验证 Task |
| B10 | External FAIL / blocked | 读源码和测试后，额外 inspect Task 返回不完整 JSON，尚未实现代码 |
| B11 | External PASS / blocked | 正确输出后验证动作为 `tool+args` |
| B12 | External PASS / blocked | 数学与 stats.json 已正确，验证动作为 `tool+args` |
| B13 | Strict PASS | 本次采样 Goal evidence 引用合法 |
| B14 | External PASS / blocked | 最后“验证源文件未变”动作混入 evidence 工具的 `source_label/source_url/end_char` |
| B15 | External PASS / blocked | 已写正确 colors.json 后，冗余创建 Task 给 write_json 混入 write_file 参数 |
| B16 | Strict PASS | 读、规范化、验证完成 |
| B17 | External PASS / blocked | 已写正确 active_users.json 后，冗余 sort Task 混入 write_file 参数 |
| B18 | External PASS / blocked | 所有 Task 完成，Goal evidence 不接受；obligation replan 两次输出非 Task batch |
| B19 | Agent completed / External FAIL | RWKV 幻觉 SHA256，后续 read_json 和 Goal commit 自证错误 manifest |
| B20 | External FAIL / blocked | “运行测试”Task 选择绝对路径 write_file，被 workspace scope 正确拒绝 |
| B21 | Strict PASS | 正确汇总并完成，存在一次可恢复的混合参数错误 |
| B22 | External FAIL / blocked | 写普通 bullet 而非 unchecked checkbox；最后验证 `tool+args` 阻塞 |
| B23 | External FAIL / blocked | primary 无效后 initial dependency 设计使 backup/selection 链不可达 |
| B24 | Strict PASS | 去重、排序、写入完成 |
| B25 | Strict PASS | model-visible root 改为 `.` 后相对路径链完成 |
| B26 | Strict PASS | 先检查根目录再创建文件，任务顺序修正 |
| B27 | External FAIL / blocked | replace count `-1` 在 Harness 中被夹为 1，只替换一个 occurrence；Goal evidence/replan 未收口 |
| B28 | External PASS / blocked | 正确 metrics 后比较 Task 输出 `tool` 加额外写参数 |
| B29 | Agent completed / External FAIL | dependency 原文完整可见，但 RWKV 选择 write_file 且只复制最后一行；后续读取与 Goal commit 自证 |
| B30 | External FAIL / blocked | 只做多次 inspect，未修改代码；read_file 又混入 `end_char` |

## 结论

Round35 证明阶段 capsule 是正确方向：它系统性减少内部状态复制、绝对路径泄漏、请求数和协议错误。但剩余问题已经分成更具体的接口层：

1. 高频 `tool+args` 只是外部表示未接入；
2. 全工具 schema 同屏导致参数跨工具混合；
3. read observation 没有把已真实计算的 artifact sha256 投影给 RWKV；
4. replace_text 的“positive count”schema 与执行期 `max(1,count)`不一致；
5. Task/Goal 判断会使用动作自产 expected 或读取自产文件自证；
6. 规划仍大量拆出冗余 verify Task。

后续必须逐项隔离验证，不能把这些都塞进格式转换层。
