> R38 实测更新：真实作者/审核/执行/导出已跑通一个命令候选，冻结按覆盖不足拒绝；预期失败测试的审核误判已修正，明确评测用途的来源不能靠计划字段重命名入训。完整项目中间步骤和多文件连续实现的数据准入尚未实证完成。详情见 data/experiments/R38/REPORT.zh-CN.md。

> 当前实现以本文末尾 R37 节为准：已有批次、读取/最终回答验证、候选导出和冻结入口。下文早期“缺少这些入口”的描述是 R36 历史状态；真实完整训练集仍未冻结。

# DeepSeek 真实轨迹纠正管线

2026-09-21：owner 已暂停训练、Agent 评测与付费生成；目前只实现和离线验证管线。
不要运行本文 `run` 操作来绕过暂停。没有自动训练、自动恢复评测、自动付费重试。

## 当前入口

`scripts/run_trace_correction_pipeline.py` 提供三个操作：

1. `prepare`：校验来源 SHA，调用生产 `replay_run` 重建原始输入与完整 token，校验对应生成前快照，冻结候选任务。
2. `run`：一次 DeepSeek 作者请求；严格协议、权限与 token 检查；另一次语义审核请求；通过后调用既有隔离编辑/命令执行验证。
3. `report`：全部任务为分母，列出未开始、拒收、异常、待审核、执行验证通过及任务族/动作分布。不会把返回 JSON 或执行成功计成训练入选。

命令均从 WSL 项目根运行：

```bash
.venv/bin/python scripts/run_trace_correction_pipeline.py prepare \
  --input data/pipeline/public_job_plan.json --output data/pipeline/jobs/example

# 暂停期间不执行；恢复生成后也必须先登记具体预算与输入。
.venv/bin/python scripts/run_trace_correction_pipeline.py run \
  --input data/pipeline/jobs/example --packet-sha256 PREPARE_RETURNED_SHA \
  --api-config data/pipeline/api_config.json

.venv/bin/python scripts/run_trace_correction_pipeline.py report \
  --input data/pipeline/job_directories.json
```

`job_directories.json` 为绝对任务目录列表，重复目录拒绝。

## 来源计划字段

计划由真实 trace 和公开任务合同登记，不由老师自由生成：

| 字段 | 含义 |
|---|---|
| source_purpose | 必须为 production_training_source；评测题不进入候选生成 |
| source_id / family | 来源身份与项目家族，供去重和覆盖审核 |
| run_root / source_files | 绝对 trace 根目录及逐文件 SHA；至少包含 RESULT、model_trace、state_snapshot，并包含完整生成前快照 |
| model_sha256 / checkpoint_id | 真实模型 SHA 与被纠正的原始生成边界 |
| context_tokens / max_target_tokens | 实际运行上限，目标不得超过当前 1800 token；超长拒收，不截断 |
| read_only / allowed_functions | 公开需求允许的动作范围；不得为了接收老师输出放宽 |
| protected_paths | 必须保护的相对文件路径，例如公开检查脚本；不能漏掉合同中要求保留的文件 |
| public_contract_provenance | 公开合同来源记录，外部验证条件不追加给老师或 RWKV |
| checks | 编辑候选的公开验证 argv；原快照必须失败，修改后全部成功 |
| expected_exit_code / expected_output | 命令候选预先登记的实际期望；暴露问题的非零退出可以有效，但必须匹配期望 |
| check_timeout_seconds | 可选，默认30秒，受既有执行验证上限约束 |

当前训练来源按既有准入规则只接受 zero profile。保留的非零 profile trace 可用于诊断，不能伪装成 zero 或用于本入口生成入训候选。
来源用途和公开合同登记仍需审核；SHA 只能证明内容未变，不能证明标注用途真实。

## API 配置与预算

API 配置包含 `directory`（共享费用账本绝对目录）、`key_file`（仓库外凭证路径）、
`model`（deepseek-flash）、`budget_usd`、`input_usd_per_million`、`output_usd_per_million`、
`max_output_tokens`、`max_requests`、`timeout_seconds`。

价格必须在恢复生成时按官方费率登记；这里不固化为永远有效的价格。
同一轮所有任务复用同一个账本，不能每个任务新建账本逃避总预算。
请求前预留保守估算费用；已知 usage 按全部输入未命中缓存估算。超时/连接中断保留预留额，不能假定未收费。
账本锁串行化请求；重启看到既有任务 RESULT 时不再次发送请求。
预算是按登记费率计算的支出门，不是供应商账单的硬额度；价格、计费异常需要单独核对。
凭证不进入请求 JSON、响应、日志或仓库。使用官方 HTTPS 地址，不重定向、不自动重试、不切换模型。

## 输出与完成边界

- PACKET / AUTHOR / REVIEW / TARGET：原始绑定、作者归属、审核证据和独立编码的目标。API生成内容不是 RWKV 原始输出。
- execution/VALIDATION：复用既有验证器的实际命令、红绿结果及来源绑定。
- VALIDATED_TARGET：执行验证通过的候选与证明引用，仍明确 training_admitted=false。
- RESULT：拒收或通过状态；不完整任务保留，不通过重新运行命令自动重试。

**尚未打通的准入边界：** 单人执行证据规则覆盖编辑和命令；读取与 final_answer 候选在语义审核后进入待准入队列，不能伪造执行事实或独立双人审核。此入口不输出可训练 dataset manifest，不自动调用 freeze/train。
后续必须补齐读取/收尾证据衔接、固定切分与近重复隔离、覆盖准入，再接既有 `freeze_direct_dataset` 的重新执行门。不能把当前执行候选模块称为“完整训练数据闭环”。

这项限制是有意显式暴露的：只产出编辑正例而不具备读取、验证和结束覆盖的批次，不应再以“数量达到1k”作为完成标准。

## 清理后的输入

data/pipeline/sources 只保留少量真实 trace 用于开发；data/test_fixtures 仅供回归，不可用于批量生成。
旧1k、历史 State 和临时脚本已删除。删除身份记录在 docs/cleanup/20260921。
只有同一冻结环境的一份 zero 基线；禁止 zero-a/zero-b 及默认重复两遍。

## R37：统一入口与可执行批次（2026-09-21）

安装后统一使用 `rwkv-lh`：`--source-workspace/--request/--output-dir` 运行单题，`--jobs` 运行批次，二者互斥。`--model`、`--base-url`、`--model-sha256` 在配置校验前应用。空任务批次报错，不再以零个任务“全部完成”返回成功。原单题脚本保留为明确的 `rwkv-lh-coding` 入口。

离线管线入口 `rwkv-lh-data` 提供：

1. `prepare --input PLAN.json --output JOB_DIR`：封存真实 trace 和模型输入边界，固定公开检查与权限。
2. `batch --input BATCH.json --api-config API_CONFIG.json`：每个边界至多一次作者请求和一次审核请求，共用落盘预算账本；全批次预检包 SHA 和重复边界。已有结果不重复付费，网络不确定错误停止后续请求。
3. `report --input JOB_DIRS.json`：按所有提交任务统计，包括拒绝、失败和未运行。
4. `export --input EXPORT.json --output REVIEWED_ROWS.json`：导出带原始输入、精确 token、来源身份、审核和验证证明的候选行。EXPORT 含 jobs、sources、vocab_size、bos_token_id；source 格式沿用 direct freeze 的来源登记，额外提供 content_reference.path。缺 collector/server attestation 时拒绝导出，禁止用虚构 SHA 填充。
5. `freeze --input FREEZE_REGISTRATION.json --output DATASET_DIR`：调用现有 `freeze_direct_dataset`，校验授权、固定回归、来源家族与内容相似度隔离、预登记覆盖、token/协议一致性，并重新执行验证。该入口不会启动训练。

读取、搜索、列目录使用 `verified_read`：在封存快照副本实际调用生产 Harness，必须成功且工作区不变。最终回答使用 `verified_final`：单人审核逐条引用原始可见输入，记录这一边界祖先中真正发生的工具结果；没有执行证据不能靠审核文字准入。这两类均存放 observation_validation，冻结时重放再验证，训练准入校验冻结证明的 SHA 和数量。旧 independent_review 标签仍需真正独立的两名审核者，不能将两次相同 API 调用冒充独立审核。

修改使用原有失败→修改→通过验证；命令使用预先登记的实际退出码与输出证据。修改、命令、读取、最终回答共享同一生产协议和 RWKV tokenizer，禁止截断目标适配长度。

R37 首批配置在 `data/pipeline/r37/`。它仅验证链路；一个来源家族不满足完整训练集覆盖。冻结准入仍有来源身份、隔离和覆盖门槛，不能将导出候选数作为合格入训数。判断语义正确与任务完整性仍依赖具名审核者，引用定位与执行成功不等于语义证明。
