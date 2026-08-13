# RWKV-LH 本地手工测试界面

## 定位

`rwkv-lh-web` 是现有 RWKV-LH Controller 的本机观察与操作界面。它不是第二个 Agent，
不引入其他模型，也不生成、筛选、修复或改写 RWKV 的答案。所有语义决策仍由同一个 RWKV
产生；页面只提交用户任务、展示已经记录的数据，并管理隔离 worker 的启动、停止和恢复。

最新冻结正式基线 Round12 为 Strict `0/90`、External `11/90`、Completed `0/90`。
因此该界面用于真实体验、复现失败和采集因果数据，不代表系统已达到 beta 或生产可用水平。

## 当前可以做什么

- 把用户自然语言请求交给 RWKV 解析为 immutable Goal 和 1--5 个 success criteria。
- 由 RWKV 规划 Task Graph、选择 action、生成 G1i action 参数、失败分析和 replan。
- 在每个运行独立的 workspace 中读取、创建、修改、复制、删除 UTF-8/JSON 文件，并执行
  Harness 允许的 workspace-scoped command。
- 用确定性 postcondition、verifier、witness intent 和 exact proof 记录完成证据。
- 持久化 Goal、Task、Attempt、Artifact、CriterionEvidence、WitnessIntent、错误、checkpoint、
  Controller event 和 model request sampling。
- 在页面中实时查看：
  - 发给 RWKV 的完整 prompt；
  - RWKV 原始输出；
  - visible text 投影；
  - parsed payload；
  - normalization 前后的 payload；
  - action/validation/recovery/obligation/witness/proof 事件；
  - Task Graph 和 workspace 文件变化。
- 停止仍在运行的隔离 worker，并从 SQLite 状态恢复 interrupted/stopped run。
- 导出一个包含 request、metadata、model trace、workspace、worker log、一致 SQLite 快照、
  state JSON 和 events JSON 的审计 ZIP。

## 当前不能做什么

- 不能稳定完成任意长程任务；Round12 的 Strict/Completed 均为 0。
- 不能把 workspace 中实际正确的结果稳定转成内部完成证据；Round12 有 11 个 false negative。
- 不能联网检索。当前 ActionHarness 没有 `web_search`，Round12 的 1,436 次原始模型响应中
  `web_search` 出现 0 次。
- 不能操作所选手工 run workspace 之外的文件。前端 seed file 和文件读取 API 都拒绝绝对路径、
  `..` 和 Windows drive path；Harness 继续执行自己的 scope 检查。
- 不能用 Codex、Judge 或其他模型替 RWKV 选择工具、证据或答案。
- 不能在 RWKV 输出无效 Goal/Plan/Action/Witness 协议时保证自动修复成功。
- 不能提供多用户隔离、认证、权限或安全公网托管。默认只能绑定 loopback。
- 当前推理服务没有声明完整 recurrent-state create/resume/fork/commit/rollback/export/import；
  因此模型上下文仍使用可审计的 prompt replay，而不是原生 RWKV state handle。

## 启动

先配置 `.env.local` 中的 RWKV endpoint、模型和必要凭证，然后在 WSL 项目根目录执行：

```bash
TMPDIR=/home/chase/GitHub/RWKV-LH/temp \
TMP=/home/chase/GitHub/RWKV-LH/temp \
TEMP=/home/chase/GitHub/RWKV-LH/temp \
uv run rwkv-lh-web
```

本机浏览器打开：

```text
http://127.0.0.1:8765
```

可以通过 `--port` 改端口，通过 `--data-root` 改手工运行目录。服务拒绝非 loopback bind；
只有显式指定 `--allow-remote` 才会解除该检查，但服务没有认证，因此不建议使用。

## 每次运行的数据来源和布局

每次点击“启动真实 RWKV 任务”会创建：

```text
data/manual_runs/runs/<RUN_ID>/
├── metadata.json
├── request.json
├── model_trace.jsonl
├── result.json
├── worker.log
├── workspace/
└── state/
    └── long_horizon.db
```

- 来源：用户在本地页面输入的任务、约束和初始 UTF-8 文件。
- 数据版本：`manual-v1`；顶层 schema 为 `rwkv-lh.manual-web-run.v1`。
- 用途：真实手工运行、失败复现、逐环节因果审计；不纳入固定 E2E-90 正式分数。
- 文件摘要：`request.json` 为每个 seed file 记录 size 和 SHA-256；workspace 列表实时显示
  size、media type 和 SHA-256；导出包包含一致 SQLite snapshot。
- 生成方式：页面 `POST /api/runs` 创建隔离目录和 request manifest，独立
  `python -m rwkv_lh.web_worker` 调用现有 Model/Controller/Harness/Store。

## 不干预保证

`ModelInvoker` 在每个请求的 trace 中分别保留 `prompt`、`raw_output`、
`normalized_visible_output`、`input_payload`、`normalized_payload` 和 `parsed_payload`。
页面只转义文本以安全显示，不改变存储值。Worker 的 `result.json` 直接写入
`ControllerResult.final_output`，并记录它是否与状态中的 `M-FINAL` 逐字相等。

格式归一化只采用产品中已经登记的透明协议边界；它可以展开允许的外壳或把 JSON string
arguments 解析成对象，但不能补 action、参数、criterion、证据、文件内容或答案。

## 建议的第一次测试

在“初始文件”中添加：

```text
路径：input.txt
内容：alpha\nbeta\ngamma
```

任务要求：

```text
读取 input.txt，在工作区创建 summary.json，包含非空行数量和按原顺序排列的 lines 数组，
然后验证写入结果。
```

即使任务失败，也应查看“RWKV 输入 / 输出”和“因果事件”，定位最早出现错误的是 Goal、Plan、
Action、Validation、Obligation、Witness 还是 Completion，而不是只看最终状态。
