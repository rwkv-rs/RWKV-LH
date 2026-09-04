# RWKV-LH 第一正式简体版 Agent 能力矩阵预登记

登记时间：2026-08-29；在 G8 checkpoint 推理、Stage B/C 和本能力矩阵执行之前。

## 目的

在联网与最小 state 引擎通过后，验证当前本地架构是否能作为第一正式简体版本投入使用：
强模型只做 Planner/Reviewer，2.9B S60 只选工具，13.3B RWKV 使用 Stage C 选出的最小
task-level state 方案完成参数、工具执行、失败恢复与原始 final。重点不是单步工具分数，
而是真实工作区中的旧 Agent 能力、联网能力及二者联动。

## 冻结能力面

先在已有、隐藏隔离验收的 RWKV-E2E 数据集中运行以下九例；不复制 acceptance 到工作区：

1. `E2E-B10`：小型实现与测试；
2. `E2E-M02`：细致 bug 修复且不削弱测试；
3. `E2E-M09`：跨文件 API 迁移；
4. `E2E-H01`：多函数实现、全测试与生成 artifact；
5. `E2E-H07`：队列语义 bug 修复、完整测试与发布标记；
6. `E2E-H10`：库存 release 多文件工作流；
7. `E2E-LH01`：逐层失败暴露后的连续修复；
8. `E2E-LH10`：35 action 内完成修复、测试、README 与 manifest；
9. `E2E-LH12`：从 REQUIREMENTS 完成中型多文件 mini-project。

另加一个冻结的 `AGENT-V1-WEB01` 真实项目：

> 创建一个简洁好看的个人记账网页，可以记录收入和支出，自动显示本月收入、支出与结余，
> 支持删除记录；刷新后数据仍保存在 localStorage。只使用原生 HTML/CSS/JavaScript，提供
> index.html、styles.css、app.js、README.md，并运行工作区内公开的功能验证脚本后再完成。

该工作区会预置公开的 `verify_app.py`，只检查用户可见契约，不包含隐藏评分或参考实现。
隔离 verifier 重新运行它，并额外机械检查四个文件存在、测试未被删除/削弱、事件链包含实际
写入和成功验证。视觉只按冻结的结构与可访问性规则机械验收，不以人工喜好替代门槛。

## 固定运行参数与对照

- physical GPU0；S60；Stage C 选择的最少 Executor state；request-last；每行/每轮首次 raw；
  hidden retry=0；postprocess=false；不修改或隐藏 RWKV 原始输出。
- 强 Planner/Reviewer 使用当前项目 `.env` 冻结配置；Planner 没有 Harness authority，工具执行
  必须全部来自 RWKV。
- max transitions=200；独立 workspace；同一 workspace 单 mutation lane；隔离 verifier
  使用只读 snapshot、无网络、无 repository mount。
- 先用 `A_GENERAL_G3` 在九个既有 case 与 WEB01 上运行同架构 control，再运行 Stage C 候选；
  case 顺序固定为上列顺序，不能只重跑有利 case。provider transport failure 只登记为
  retryable external failure，业务失败不得隐藏重试。

## 固定门槛

1. WEB01 必须 external pass、agent completed、公开 verifier exit0；缺一项即不具备用户示例能力。
2. 九个既有 case 中候选 external pass `>=8/9`，其中 `E2E-M02`、`E2E-H07`、
   `E2E-LH12` 必须通过；completed `>=8/9`。
3. 相对 G3 control：strict/external 净增益均不得为负；control strict-pass case 的回归数=0；
   首次偏离按固定分类报告，不能用最终成功掩盖中间错误。
4. 联网联动沿用 Stage B 的 live V1 2/2、V2 6/6、retrieval9/9，并追加一次
   “公开资料查证→本地文件修改→本地测试→RWKV final”的完整任务；引用字段只能来自已提交
   evidence span/structured field，网络失败必须进入明确恢复而非伪造事实。
5. 每个 run 的 Selector/Executor profile switch=0；Planner 工具调用=0；RWKV raw output
   modification/deletion/reorder/hide=0；scope violation=0；隐藏 acceptance 泄露=0。
6. 完整项目测试、边界、异常和历史联网回归全部通过，`git diff --check` 通过；所有实验记录
   写入 `data/experiments/`，并记录源码、数据、状态、引擎与输出 SHA-256。

若 WEB01 或关键 case 未通过，第一正式版本结论必须是 `not_ready`；失败簇用于下一轮
state-tuning 数据，不能通过测试用例特判、提示词答案注入、Controller 修补或降低门槛发布。

## WEB01 冻结身份

以下内容在任何 WEB01 模型调用前生成并冻结：

- suite manifest：`benchmarks/rwkv_e2e/rwkv_agent_v1/manifest.json`，SHA-256
  `c42ab96bd34bfd8b3150250b54e2dab31bda2aa483ef69ad6851483832a172a2`；
- visible tasks：SHA-256
  `87f54fabcf2584ebc74840559e4abb86b31e5e9744c4037d052c318e884c176f`；
- hidden acceptance：SHA-256
  `0fae91dfd7ed78afc0139ba4fea6f0566d1288d33acfb62097ed88d1d6f6a19f`；
- deterministic generator：SHA-256
  `06ccd36f5e01865eee0b705dffbf051c2b51ef2d058031ffffa861c52e4ebf46`；
- E2E runner：SHA-256
  `d45ed6bb3aa08578b60661de662838cadb690c51cab6cdc36dd4ff4815009c80`。

`uv run rwkv-lh-e2e --suite agentv1 --validate-only` 已在 WSL 返回 catalog valid；
对应目录来源、版本、用途、生成脚本与全部文件摘要均记录在 manifest。acceptance 不进入
workspace；公开 `verify_app.py` 进入 workspace，隐藏 verifier 同时逐字校验该文件未被修改。
