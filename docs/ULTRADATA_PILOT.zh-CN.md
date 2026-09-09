# UltraData 首轮任务准备与使用

本轮 `ULTRADATA_PILOT_R1_20260909` 按 owner“先做 Tool-Use／Code-Agent 与可执行 Code 任务”推进。完整范围、来源与验收在 [实验目录](../data/experiments/ULTRADATA_PILOT_R1_20260909/PLAN.zh-CN.md)。这是外部任务准备，不是正式角色数据集，也不恢复此前暂停的整套 Agent 评测或训练。

## 已有入口

`rwkv_lh.ultradata` 负责范围 SHA 核验、完整 JSONL 行审计、SFT 结构观察和 std-I/O 任务编译。`scripts.prepare_ultradata_pilot` 负责固定选择、逐行清单与隔离验证，执行后端复用 `rwkv_lh.benchmark_verifier.run_isolated_verifier`。

没有新增 Controller、角色协议或模型调用。Code 公开任务保留原 query，仅追加统一 Python 3/stdin/stdout/预算合同；ground_truth 只编入私有 `project_behavior`，验证期间使用只读 workspace snapshot、隔离网络及隐藏验证程序的子进程。所有发布测试都执行；仅去掉输出末尾空白，不忽略前导空白或内部差异。

## 本地重建

以下在 WSL UbuntuRecovered、仓库根目录执行。首次抓取的 6 个固定范围保存在实验 `raw/`，URL、revision、字节数和 SHA 在 `FETCH_MANIFEST.json`；工具不下载或执行外部轨迹中的命令。

```bash
.venv/bin/python -m scripts.prepare_ultradata_pilot prepare \
  --fetch-manifest data/experiments/ULTRADATA_PILOT_R1_20260909/FETCH_MANIFEST.json \
  --output data/experiments/ULTRADATA_PILOT_R1_20260909/rebuilt_bundle
```

输出目录必须不存在，原选择与验证记录不能覆盖。产物：

- `public/tasks.json`：现有 runner `run_case()` 使用的公开任务对象，seed 为空；仅 Agent 自己创建文件。
- `private/acceptance.json`：同一 runner 的私有验收对象，绝不复制到 Agent workspace。
- `AUDIT.jsonl`：每条完整源行的路径、revision、行号、字节偏移与 SHA、审计去向。无效行和尾部残行分别登记。
- `MANIFEST.json`：固定选择、数据与协议/工具 SHA、覆盖、重复检查、可见性与证据边界。

原始片段和编译后的外部题目/测试不纳入 Git；取得清单中相同 revision 的字节范围并核验 SHA 后可重建。清单保存的是范围 SHA，并不声称下载或核验了整份大分片。此次首尾位置抽样不是随机抽样，也不是全库审计。

## 验证候选程序

将候选 `main.py` 放入专用 workspace，再运行：

```bash
.venv/bin/python -m scripts.prepare_ultradata_pilot verify \
  --bundle data/experiments/ULTRADATA_PILOT_R1_20260909/bundle \
  --task-id ULTRA-Code_00001 \
  --workspace /absolute/path/to/candidate_workspace \
  --output data/experiments/ULTRADATA_PILOT_R1_20260909/new_candidate_check
```

编译文件必须与 manifest SHA 相符，候选在隔离 verifier 内运行；命令返回 0 代表该候选通过所有发布 I/O 测试。测试、参考实现及作者交付不形成角色训练证据。`RESULT.json` 不应提供给 Agent，后续生产工作需定义与验收隔离的公开反馈。

任务对象与现有 `run_case` 接口兼容，本轮没有将试点注册到固定 `SUITES`、没有修改原评测分母、没有执行真实模型采集。正式采集前仍须冻结模型/服务/State/源码/预算与目标角色 scope，核验完整 trace 后走唯一角色抽取器；不能把作者参考代码当作 Executor 正例。

## 选择结论

1. 可执行 Code 首批固定三题已验证，适合下一轮外部任务执行采集。它们是算法程序生成题，不能代表仓库维护、Web 或全栈能力。
2. Tool-Use 保留工具定义、调用、回包与逐轮 loss 信息，用于研究必要信息收集、工具选择和边界。无回包或澄清轮次不能当成成功；源工具 schema 不是可执行 handler，需要原环境与初始数据库才能重建。
3. Code-Agent 用于研究定位→修改→检查→交付的连续行为。初始仓库版本、依赖及独立验收没有在该发布物中提供，不能根据教师改动倒造初始环境并声称真实复现。
4. MiniCPM5-2B 保持 P0 方法参考：重视数据的专项作用、监督掩码、实际结果和成本；后续在固定回归上验证混合收益，再决定训练配比。外部工具名、轨迹中的自述成功和内容长度都不是本项目角色标签。

当前真实角色样本和 optimizer steps 均没有因本轮准备增加。外部任务之间及与公开开发集的全面近重复/来源审查仍属正式采集前工作；本轮只对试点选择做 byte 5-gram cosine 检查，未读取 Holdout。
