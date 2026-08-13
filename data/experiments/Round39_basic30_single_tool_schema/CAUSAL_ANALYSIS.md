# Round39 Basic30 单工具 schema 纠正因果分析

## 固定结果

| 指标 | Round36 | Round39 | 变化 |
|---|---:|---:|---:|
| Strict | 14 | 14 | 0 |
| External | 21 | 22 | +1 |
| Agent completed | 18 | 20 | +2 |
| FP | 4 | 6 | +2 |
| FN | 7 | 8 | +1 |
| 模型请求 | 406 | 406 | 0 |
| Task | 135 | 127 | -8 |
| Attempt | 134 | 137 | +3 |

Round39 没有形成净提升，且 FP/FN 同时增加，不满足上传条件。本轮不提交、不推送。

- Strict PASS：B01、B02、B03、B05、B06、B07、B08、B09、B11、B13、B14、B15、B17、B24。
- FP：B04、B20、B22、B27、B29、B30。
- FN：B12、B16、B18、B19、B21、B25、B26、B28。
- Agent 与 External 均失败：B10、B23。

## Round39 机制实际命中

`rwkv_selected_single_schema_correction` 共命中 15 次、分布在 10 题：B05、B10、B12、B15、B16、B17、B19、B23、B25、B28。

机制边界符合预注册：每次都由第一次 RWKV 响应给出已注册工具 identity，第二次只显示同一个 schema，事件均记录 `controller_selected_action=false`。未知工具或无法解析的 identity 没有被 Controller 猜测。

但它只修复“工具已选对、参数 schema 混合”的表示/接口问题，不修复错误工具选择、不可执行的 Task、模型对观察的错误判断和 Goal 假证明。因此定向 canary 的收益没有稳定转化成 Basic30 净提升。B25 canary Strict PASS，正式运行中虽然写入结果正确，仍在冗余验证 Task 阻塞，说明参数纠正只是上游一个局部环节。

## 从首个错误环节向后追溯

### 一、FP：生产错误被 Task 自证，再被 Goal 批量放大

#### B04：缺失数据依赖 → 模型臆造 copy 内容 → 自产 expected → Goal 弱证据通过

1. 规划阶段的 T3 是“原样复制 source.txt”，却只依赖创建目录的 T2，没有依赖已读取 source.txt 的 T1。
2. action capsule 因而只有“directory created”，没有源文件内容；RWKV 没选已有 `copy_file`，而是 `write_file` 并臆造 `This is the source file content.`。
3. deterministic `file_content` 的 expected 来自同一 RWKV action 参数，只证明“执行结果等于模型刚提交的内容”，不能证明“等于 source.txt”。
4. Task cross-check 继续以 action 与 post snapshot 一致为由通过。
5. Goal 的 GC2 要求 copy 与 source 相同，RWKV却绑定只含 `file written` 的 `M-T3-A1` 到 GOAL，reason 只声称“文件存在”；批量 decision 仍为 pass。
6. 外部 `files_equal` 发现两个 SHA256 不同。

首个错误是规划缺少真实数据依赖；错误动作、自产 expected 和弱 Goal 绑定依次放大。

#### B20：模型修改了测试语义 → 自己运行的新测试通过 → Goal 接受

RWKV先正确实现 `is_even`，随后又覆写用户测试文件为一个普通函数脚本。`python test_parity.py` 退出 0，但外部固定入口 `python -m unittest -v test_parity.py` 报告 0 tests、exit 5。系统只证明了模型自己选择的命令和被模型修改后的测试通过，没有保护测试作为独立期望源。Goal 将该运行结果当成用户验收通过。

#### B22：错误 Markdown 语义 → read-back 自证 → Goal 未比较细节

RWKV把 unchecked item 写成普通 `- item`，T3 read-back 精确观察到了错误文本。Goal 对 GC3/GC5 仍声称“unchecked / exact”，实际 ref 中没有 `[ ]`。格式层没有改变内容，错误来自 RWKV语义与 Goal 裁决。

#### B27：操作次数不足 → recovery 再做一次仍不足 → Goal 把 action summary 当完成事实

目标有三个完整 `protocol=v1` occurrence。两次 `replace_text(count=1)` 后仍剩一个。Round38 已正确拒绝非正 count 且不再静默改参，但本次 RWKV每次只选择合法的 1。最后 Goal 将 `M-T3-A2` 的动作摘要解释成“没有 v1”，没有绑定包含最终完整文件内容的强观察。

#### B29：读取完整源文件 → 只写最后一行 → 多次覆写 manifest → Goal 弱证据通过

T1 已观察 `immutable payload\nline two\n`；T2 只向 backup/source.txt 写入 `line two`。之后三个 Task 重复写 manifest，未纠正 producer。Goal用 `file written` 摘要声称 backup 与 source相同。首错是 RWKV生产动作；规划冗余和弱证据绑定放大。

#### B30：没有任何生产动作 → Goal reason 明确否定 → 全局 decision 却是 pass

五个 Task 全是 read/list，`names.py` 仍含 `NotImplementedError`。Goal 的四个 binding reason 明确写出函数未实现、测试不能通过，但同一个多 criterion 响应顶层仍给 `decision=pass`。当前协议只机械验证 ref 和字段，无法把自由文本 reason 的否定语义改成 replan；这也是最直接的“多项局部判断与一个全局 verdict 脱节”证据。

### 二、FN：结果正确，但不可执行验证 Task 或 Goal/replan 协议阻塞

#### B16、B19、B25、B26、B28：验证 Task 不是一个可独立执行的 Harness action

- B16：read_file 返回完整 32 字符且 metadata 可证明 `complete=true/truncated=false`，Task verifier仍认为 max_chars=32 可能没读全。
- B19：真实 ArtifactRecord 已给 payload SHA256，manifest 也正确；验证 Task 反复 read_json/read_file，却要求单个 action “产生 digest bytes”。
- B25：settings.json 完全正确；read_json 已返回精确结构，verifier一度误解 nested 字段，随后又认为“读取不是验证”。
- B26：recursive listing 明确标注三项 `type=file` 加一项 `type=directory`，verifier把四个 entry 误当四个文件。
- B28：第一次 read_json 已得到正确 metrics.json，依赖中已有 metrics.txt；verifier认为读取动作本身没有执行比较。恢复随后把 read_json 用到 metrics.txt，产生 JSONDecodeError。

共同首因是 planner仍生成“比较/验证”语义 Task，而一个 atomic Harness action只能产生新观察，不能同时代表跨来源比较结论。RWKV Task cross-check本应完成比较，却错误要求 action自身另行输出 verdict；recovery只换/重试 action，没有改变不可执行的 Task contract，最终耗尽。

#### B12、B18、B21：Task 全完成，Goal 绑定一次失败，replan 外壳再次失败

三题 workspace 均通过外部验收：

- B12 Goal实际/期望绑定到了同一 `stats.json` path lineage；
- B18 绑定了相同 ref；
- B21 没覆盖每个 criterion 恰好一次。

机械 provenance validator 正确 fail-closed。随后 goal-obligation replan 的 RWKV 输出却回到旧的完整 Task 状态或额外字段，而不是唯一 canonical task batch，第二个协议错误把可完成结果变为 blocked。这里不能靠格式层删除额外语义字段使其通过；需要简化 Goal 裁决粒度及恢复协议。

### 三、真实生产失败

- B10：RWKV实现 `lower().replace(" ", "-")`，没有 trim/折叠空白；真实测试失败。随后 correction 输出含未知 `tool/tool_id`，系统正确拒绝。
- B23：primary.json 是坏 JSON。T1 recovery在 primary/backup之间摇摆，但 Task contract始终要求观察 primary；没有把“读取失败”作为分支条件推进到选择 backup 的后续 Task，最终耗尽。

## 格式层边界结论

Round39 的失败不能通过扩张格式层解决。格式层只负责把已登记的常见 wire 形式映射为 canonical `name + arguments`，且必须保留所有语义字段和值。它不得：

- 选择或切换工具；
- 删除跨工具参数以让调用通过；
- 从 Goal/Task 补内容、count、path 或答案；
- 把失败 reason 改成 replan；
- 根据外部验收筛选结果。

## 下一步结构顺序

1. **逐 criterion、原子聚合的 Goal 裁决**：每次只判断一个 criterion，只绑定一对 actual/expected；任一 replan/协议失败则整批不提交，消除 B30 这种局部否定与全局 pass 脱节。先独立消融。
2. **canonical 强观察目录**：同一 Attempt 若有 post-action snapshot，则 Goal目录不再同时展示低信息的 `file written/JSON written` 摘要；权威状态仍完整保留并审计。减少 B04/B22/B27/B29 的弱证据自证入口。
3. **观测型验证 Task 语义**：明确 RWKV cross-check本身就是跨依赖观察的比较者；Harness action只负责取证。完整 read metadata、ArtifactRecord SHA256、entry `type` 都是可比较事实，不要求工具另产一个 verdict。
4. **恢复按失败层分流**：action失败才换 action；Task contract不可由一个 action完成时回到 task frontier；Goal binding格式失败只重试单 criterion协议，不生成旧完整状态外壳。
5. **工具选择与参数绑定分阶段**：若继续降低弱模型的工具/schema混淆，应由 RWKV先从紧凑 action catalog选工具，再由同一 RWKV在单 schema下给参数；Controller始终不做语义选择。此项与 Goal整改分轮验证。

每项必须分别预注册并固定跑离线回归、LH-Control、E2E catalog、定向 canary 与 Basic30；不能把多项一起改后主观归因。
