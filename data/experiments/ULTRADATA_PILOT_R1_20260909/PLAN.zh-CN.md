# UltraData 首轮接入：冻结范围与验收

Owner 本任务明确要求“现在开始”“先做 UltraData Tool-Use／Code-Agent 与可执行 Code 任务”。本轮落实数据筛选和可执行任务准备，不恢复 owner 已暂停的整套 Agent 评测或训练。

## 范围（在本轮新增样本读取与执行前登记）

- 来源：openbmb/UltraData-SFT-Agent-2609 的 Tool-Use、Code-Agent；openbmb/UltraData-RL-2609 的 Code。使用已有审查冻结的 revision，禁止混入未绑定 revision 的 viewer 数据。
- SFT revision：`f684cc1a9f3e19f6f4929102cd9b06cc0b895b8a`；RL revision：`e6ecfa733708a4c54b5a98c3ca0fd16fc6923790`。
- 位置抽样：各方向按文件路径排序的首、尾 JSONL 分片，各读前 4 MiB，最多 24 MiB 原始数据。所有完整行进入审计；尾部残行只登记，不补造。此样本不代表整库分布，不估算全库合格比例。
- 先检查结构、工具调用与回包、监督掩码、环境材料、外援依赖线索、长度与重复。自动规则只作结构诊断及复核提示，不作成功标签或角色操作标签。
- 可执行 Code 试点：按源文件路径与行号顺序，选前三个结构合格且不与先选任务构成 byte 5-gram cosine >= 0.95 的 std-I/O 任务。选定后不按执行成绩换题；失败保留并报告。
- 沿用当前唯一 Harness／隔离 verifier；公共 workspace 只含原始题目和统一 Python 提交合同。源 ground_truth、私有测试、参考实现、mutant 和教师轨迹不进入 workspace。
- 参考实现由本轮独立编写，仅用于数据及验证器验收，不作 RWKV 输出或训练目标。每题验证所有发布测试，并用错误实现检查拒绝路径。

## 验收与资源

- 数据级：读取的完整行 100% 留审计去向；保留 source revision、文件路径、行号、逐行与范围 SHA；缺失事实明确记录。
- 代码级：前三题全量发布 I/O 测试能在现有只读 snapshot／无外部网络验证器内执行；每题参考通过、至少一种语义错误变异被拒绝，否则该题不标 ready，不换题。
- 接入边界：无外部静态轨迹被标为生产 trace；无生成的角色协议字典；无训练集／dev／confirmation 新切分；无 Holdout 访问。角色覆盖仅报告潜在场景，当前合法角色样本数仍取真实抽取结果。
- 工程级：新增行为先失败后通过的回归；完整 `.venv/bin/python -m pytest -q tests/`，Torch、State 注入及浏览器不得跳过。
- 本轮 CPU 研究与验证；外部命令仅隔离执行，Code 每用例最多 3 秒、每题 verifier 最多 180 秒；不下载模型、不启动优化器。
- MiniCPM5-2B 为 P0 方法参考：数据按能力缺口及真实验证筛选；保留失败恢复与 loss mask，后续按实际收益确定训练配比，不根据样本总数预设比例。

## 报告与后续

先报告 Agent Strict／completed／mutation／终止原因是否测量，再报告角色样本数和本轮数据/验证器成绩。最终产物为可重复的审计与 Code 接入工具、来源清单、固定三题包、执行验收与局限记录；正式模型采集需另外冻结实际模型/服务/预算，不能冒称本轮已有 Agent 改善。
