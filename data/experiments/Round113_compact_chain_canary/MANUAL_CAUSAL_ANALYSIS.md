# Round113 定向 14 题逐题因果分析

## 固定口径与结果

- 代码版本：Round113 `long-horizon.run.v14` 工作树，测试开始后保持冻结。
- 用例：`E2E-B01,B02,B04,B10,B11,B14,B15,B18,B22,B23,B25,B27,B29,B30`。
- Strict E2E：`4/14`；Round112 同组为 `0/14`。
- 外部结果正确：`7/14`；Round112 同组为 `4/14`。
- TP/FN/FP/TN：`4/3/5/2`；Round112 同组为 `0/4/7/3`。
- 终态回答：`14/14` 非空，且所有有效 `lh_final_answer.text` 均原样交付。

Strict E2E 只统计 Agent `completed` 且隔离外部 verifier 通过。TN 不是 Strict 通过，但用于识别假阳性是否下降。

| 题目 | Round112 | Round113 | 最早错误环节 | 后续放大链 | 归因 |
|---|---|---|---|---|---|
| B01 | FN | FN | Task 已写入正确文件并成功执行精确 `grep`，但没有提交 `lh_task_done` | 重复成功 verifier 直到 32 次上限，重规划继续重复，最终 blocked | 提交协议显著性不足；代码侧没有把 `completion_protocol_ready=true` 转换成紧凑的完成检查点 |
| B02 | FP | TP | 无 | 单一端到端 Task 依次读取、计算、写入、读回；Goal 二次自审后完成 | Round113 结构有效 |
| B04 | FN | FN | T1/T2 已正确产生两个输出；T3 声明 `command_execution`，却只执行目录/文件读取 | 未运行声明的命令，随后重复读取和格式漂移；重规划又复述完整旧计划而非只替换 T3 | 首因是 RWKV 工具选择错误；格式漂移与宽重规划放大 |
| B10 | TN | TN | 初次选择 `python -m pytest`，沙箱错误地启动基础 Python，报告没有 pytest | 浪费恢复预算后改用 unittest；模型仍不能根据失败 diff 修正连续空格 | 首因含真实运行时接口缺陷；最终外部失败仍有模型编码能力因素 |
| B11 | TN | FP | Goal Task 的 `evidence_subject` 错指输入 `name.txt`，随后把未转换文本原样写入输出 | 任意成功的后置只读命令被当作充分观察，错误 Task 被允许提交，Goal 自审也确认 | Task 证据主体与实际 mutation target 未绑定；其后是 RWKV 语义错误 |
| B14 | FP | FP | 第一版 `merged.txt` 实际完全正确，RWKV 用 `cat merged.txt` 读回并提交完成 | 证据层只承认专用 `read_file`，拒绝真实 `cat` 内容观察；32 次重复后重规划覆盖正确文件为字面占位文本 | 通用证据接口缺陷是首因，恢复流程放大并破坏正确产物 |
| B15 | FP | FP | RWKV 将要求的 `{\"colors\":[...]}` 写成顶层数组 | 写入 effect check 只证明文件等于模型自己提供的字节，独立读回仍被 RWKV误判为满足 Goal | 模型 JSON 结构语义错误；`checks` 命名容易放大同源证据错觉 |
| B18 | FP | FP | RWKV 把折后总价算成 `92.0` 而非 `68.0` | 写入、读回和两次 Goal 完成声明都围绕同一错误值 | 模型算术错误，不允许控制器替换答案；effect check 展示需要去语义化 |
| B22 | FP | FP | RWKV 在标题后添加了验收不允许的空行 | 精确读回后仍提交完成，Goal 自审未识别 exact-content 差异 | 模型精确格式判断错误 |
| B23 | FP | TN | RWKV 把 primary/fallback 拆成 AND 依赖图，但 `after` 不表示条件分支 | primary JSON invalid 后，Task 反复读取；Goal 重规划反复复述同一不可行分支 | Round113 阻止了错误完成，但暴露条件流程规划说明不足 |
| B25 | FP | TP | 无 | 端到端读取两个输入、合并、写入、读回并完成 | Round113 结构有效 |
| B27 | TN | FN | 文件已正确替换，`grep -q` 返回 1 正是“无匹配”的期望结果 | command harness 固定把非零当失败，Task 看不到可提交的结构证据，随后进入重复/重规划 | 命令接口缺少模型显式声明的预期退出码 |
| B29 | FN | TP | 无 | 单 Task 完成复制、manifest 写入和读回 | Round113 结构有效 |
| B30 | FN | TP | 无 | 单 Task 写代码并运行真实测试，随后完成 | Round113 结构有效 |

## 跨题根因

### 1. 真实环境能力没有完整暴露给 Agent

`python` 在 bubblewrap 内通过 `Path.resolve()` 丢失虚拟环境身份，实际启动只包含基础标准库的解释器；因此项目已安装的 pytest 对 Agent 不可用。B10 的第一次测试失败不是模型能力问题，而是运行时接口问题。

### 2. 证据类别比真实观察方式更窄

B14 的 `cat merged.txt` 已返回完整文件内容，却不被 `file_content_read` 接受。证据类别应描述“实际观察到了什么”，不应硬绑定唯一工具名。控制器仍不得判断内容是否满足自然语言 Goal；该判断继续由 RWKV 所有。

### 3. 命令执行被错误等同为退出码 0

B27 的 `grep -q` 退出码 1 是预期证明。当前 action contract 没有 `expected_exit_code`，把基础设施执行成功与业务断言成立混为一谈。预期退出码必须由 RWKV 在调用中明确给出，控制器只比较实际值，不从 Goal 或结果反推。

### 4. mutation 与证据主体没有结构绑定

B11 声明观察输入 `name.txt`，却修改 `normalized_name.txt`。只要 Task 产生 workspace mutation，其路径型 evidence subject 至少应指向本 Task 的一个实际 mutation target；否则完成协议还没有观察最终产物。

### 5. effect checks 的展示容易被误读为语义验收

`file_content` 对写操作只证明文件等于同一个模型调用提供的 content，并不证明该 content 等于用户要求。事件应明确标为 operation-effect checks，并声明它不验证 Task/Goal 的自然语言语义。

### 6. completion-ready 状态没有形成紧凑决策点

B01 在证据齐全后重复成功 verifier 数十次。`completion_readiness` 虽已存在，但与普通 action result 混在一起。需要在 ready 时给出紧凑、条件式、精确线格式的下一步：由 RWKV 比较实际输出与 `done_when`，成立才提交，否则必须选择不同操作。

### 7. 条件任务仍被错误建成 AND 图

`after` 是必需依赖，不是 if/else。fallback、重试和按结果选择的普通流程应优先保留在一个端到端 Task lane 内，让同一个 RWKV 状态根据实际 outcome 继续；当前规划说明对此不够明确。

## 不应由架构代做的错误

- B11 的标题化与 acronym 保留、B15 的 JSON 顶层结构、B18 的算术、B22 的精确空行均为 RWKV 语义判断。
- 控制器可以确保实际输出可见、证据来源独立、完成决策再次交给 RWKV，但不得替换值、补字段、改文件或自动判定自然语言 Goal 已满足。
- 外部 verifier 只用于实验评分，不能回流给单次 Agent 决策。

