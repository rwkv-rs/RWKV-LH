# Round88 全调用逐题因果分析

## 结果

- Strict E2E `1/4`，Agent `1/4`，External `3/4`。
- B03 从 Round87 的 External/Agent/Strict 全失败提升为三者全通过。
- 四题的用户可见回答均非空，且四题都与各自 RWKV Final lane 的
  `lh_final_answer.text` 精确一致；blocked 不再等于静默。
- 没有假阳性；B01、H04 是假阴性。

## 逐题链路

| 题目 | 最早模型决策 | 接口/执行 | 恢复与完成 | 结论 |
| --- | --- | --- | --- | --- |
| B01 | Goal 与首次 `write_file` 正确。写后 RWKV 直接输出 `lh_task_done(params.task_id=T1)`，语义正确但不是唯一 wrapper 形状。 | direct control 被协议层回退；模型重写一次文件，随后 wrapper done 被独立观察 gate 拒绝，再正确 `read_file`。之后却选择 `read_json` 解析纯文本，形成一个真实失败 Attempt。 | 相同 `read_json` 的后续候选都在 Attempt 前抑制并 rewind，但模型仍连续复读，第四次进入 unchanged loop。外部文件精确正确；Final 正确说明 blocked 与 JSONDecodeError。 | pre-Attempt 与回答链已正确；剩余最早结构问题是 Task 接口只接受 wrapper，而模型频繁使用携带显式 task_id 的 direct G1i 表达。一次真实错误后，同 lane 即使 rewind 仍有模式粘滞。 |
| B02 | Goal 仍只生成“读取并提取输入”的第一批 Task；首次 `read_file` 正确并获得全部 `project/count`。 | RWKV 随后误选 `read_json`，真实失败一次。 | 五次同调用均未再次执行且被 rewind，但模型没有转为 Task done；T1 未完成，Goal 无法产生 report 写入批次。Final 非空且忠实报告失败。 | 事务修复限制了副作用和 Attempt 数，却没有重置已经被真实失败固定的 recurrent/prompt 模式。 |
| B03 | Goal 正确给出 read→update→verify 三 Task。首次 T1 输出带多余 wrapper 外字段，被协议回退；纠正后完整 `read_json`。 | RWKV 先用 direct done（协议回退），随后在 T1 内正确 `write_json` 保留所有字段，再读回；T2、T3 均读回并完成。多个 direct control 或多余字段只造成格式重试，没有改变操作参数。 | Goal 的 `lh_goal_done` 携带观察注释，由 void-control 兼容层接受；Final 精确描述成功。 | 事务回退、紧凑 cursor observation、void control 兼容共同使全三段链完成，证明改动具有正向因果效果。 |
| H04 | Goal 和写入完全正确；写后 direct Task done 仍因 wrapper 形状回退。 | 重写被 unchanged 抑制；wrapper done 触发独立读取要求；一次缺 path 的 `read_file` 被协议回退，随后正确读取并确认精确文本。之后又误选 `read_json`，真实失败一次。 | 后续 `read_json` 全部 pre-Attempt rewind，但保持复读直到 blocked。外部三个安全/内容检查全过；Final 非空且未谎报完成。 | 假阳性已稳定消失，scope/内容均正确；假阴性与 B01 同源：direct control 形状摩擦 + 真实失败后的 lane 模式粘滞。 |

## 本轮证明与未解决项

已证明：

1. Rewind 确实阻止重复候选进入下一 checkpoint，B01/B02/H04 都只产生一个
   `read_json` 失败 Attempt，而不是每次复读都执行。
2. `lh_goal_done` 附带可见注释不再卡住完成层，B03 通过。
3. 紧凑完整读取投影使 B03 不再把 `byte_end` 当下一游标。
4. terminal response 不依赖 run completed；四题均获得原始 RWKV 回答。

未解决：

1. Task lane 仍只认可 wrapper；三个用例都出现了语义完整、显式携带 `task_id` 的
   direct `lh_task_done`。这是最常见的第二种 G1i 表达，不应被当作语义错误。
2. 一次真实失败必须保留在历史中，但连续相同的未执行候选表明恢复仍需确定性
   state capsule/branch reset；仅 rewind 最近候选不够。
3. B02 的第一批 Task 完成前无法回到 Goal，说明 Task recovery 的质量直接决定
   分阶段计划能否继续，不能把它误归因于 Goal 没有一次生成完整计划。

## 下一步

- 格式层通用接受 direct Task representation，但仅在 RWKV 自己同时输出一个显示的
  operation 名和显式 `task_id` 时转换；不得从 active Task 补 id，也不得改 operation args。
- 当同一失败指纹/unchanged observation 连续出现时，用权威 Task、已观察 Attempt 与
  rejection 确定性重建同一 Task lane 的 recovery capsule，切断错误 Assistant 模式；
  不删除失败证据，不替模型选下一 operation。
- 扩大固定 canary 后再运行完整 90 题，继续统计 Strict、FP/FN、回答非空率与 raw match。
