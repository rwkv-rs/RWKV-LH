# Round36 Basic30 `tool + args` 格式层分析

## 结果对比

| 指标 | Round33 | Round35 | Round36 |
|---|---:|---:|---:|
| Strict | 5 | 10 | 14 |
| External | 21 | 20 | 21 |
| Agent completed | 7 | 12 | 18 |
| FP | 2 | 2 | 4 |
| FN | 16 | 10 | 7 |
| 请求 | 472 | 383 | 406 |
| Task | 160 | 128 | 135 |
| Attempt | 116 | 110 | 134 |
| model contract error | 118 | 18 | 15 |
| action argument rejection | 16 | 14 | 7 |

Round36 的请求/Attempt 高于 Round35，主要因为更多题越过最后动作格式并继续执行；不能把增加的执行量直接解释为效率退化。Strict 从 10 提高到 14，FN 从 10 降到 7，说明高频格式接入有实效。

## 通过与失败分组

- Strict PASS：B01、B02、B05、B06、B07、B09、B11、B12、B16、B17、B18、B20、B24、B28。
- External PASS 但 blocked：B03、B13、B14、B15、B21、B25、B26。
- Agent completed 但 External FAIL：B08、B19、B22、B27。
- Agent 与 External 都失败：B04、B10、B23、B29、B30。

## 格式层实际作用

B01、B02、B11 的主要产物在 Round35 已正确，Round36 让其最后 `tool+args` 动作进入 canonical G1i；三题直接 Strict PASS。B12 在定向 run 中还暴露 `read_json.start_char` 并阻塞，但正式 Basic30 的采样没有该额外参数，最终 Strict PASS。格式层没有删除任何参数。

Round36 action argument rejection 从 14 降到 7，但余下 7 次均不是表示差异：write_json 混入 `create_parents/overwrite`、read_file/read_json 混入另一工具参数、缺参数或绝对路径。这些仍被 Harness 拒绝。

## 格式可达后暴露的主要结构问题

### 自产 expected 与自证

B08、B19 都读取了 payload 文本，但 action capsule 没有呈现 read tool 已真实计算并记录的 artifact sha256。RWKV自行生成错误 digest，write verifier 又把该 action 参数作为 expected，因此验证“写入与自己提交的错误值一致”；随后 read_json 和 Goal evidence 再次接受自产文件。

B22 将 unchecked item 写成普通 bullet，B27 只替换一个 occurrence，也通过了类似的“写入/读取自己的产物”链。假阳性从 2 增到 4 不是格式转换篡改答案，而是格式阻塞消失后，证据角色缺陷变得可观察。

### 接口事实未投影

read_file 的真实 ActionResult 已包含 `artifacts[].sha256`，但 phase observation 只有 content 与 pagination metadata。对于 hash 任务，架构明明掌握真实工具观察，却迫使 RWKV 从文本自行计算 SHA256。这是接口投影缺失，不是模型最终答案问题。

### 工具 schema 混合

B14、B21、B25、B30 等仍把另一个工具的参数放入所选 action。当前一个 prompt 同时给出全部工具的完整 schema，弱模型容易跨 schema 复制。正确结构候选是由 RWKV 先显式选择工具名，再只向 RWKV 展示该单一工具 schema 来绑定参数；控制器不能按 Task 语义替它选择工具。

### replace_text contract 不一致

B27 的 G1i schema描述 `count` 为 positive integer，但缺少 minimum；模型提交 `-1`。执行端用 `max(1,count)`静默变成 1，产生与提交值不同的执行语义。这是接口实现缺陷：validation 应拒绝非正数，执行端不得静默 reinterpret。

## 结论

Round36 的纯格式改动应保留，但当前 4 个 FP 说明尚不满足上传条件。下一步优先把真实 observed artifact metadata 投影给 RWKV，并消除执行端对参数的静默 reinterpret；随后再独立验证两阶段工具 schema disclosure 与非自引用 Goal/Task evidence。
