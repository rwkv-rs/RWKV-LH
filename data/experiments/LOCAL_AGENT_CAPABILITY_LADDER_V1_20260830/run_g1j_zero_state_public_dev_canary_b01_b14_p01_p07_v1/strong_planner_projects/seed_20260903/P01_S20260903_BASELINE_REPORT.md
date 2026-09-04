# P01 run label 20260903 全 zero State 完整项目 Agent 基线

## 结论

- 分类：`valid_zero_state_capability_failure`。
- Goal 终态 `running`，消耗 240 transitions；完整项目未成功。
- 正式轨迹包含 239 次 RWKV 请求和 1 次 Strong 请求。
- 独立黑盒验收 2/7 项通过；最终工作区含 0 个文件或链接。

## Planner 阶段结构

- 计划 revision `1`，共 5 个步骤，完成 0 个。
- 当前阶段：`1`；完成阶段：`[]`。
- 最终 frontier：`["S1"]`。
- 嵌套阶段 JSON：`[{"stage":1,"steps":[{"accepted_evidence_refs":[],"allowed_operations":[],"constraints":["保持公共数据模型可被 CLI、执行器和测试复用；不得使用内存状态替代持久化设计。"],"depends_on":[],"objective":"建立 Python 3.11+ 项目骨架和 taskforge 核心领域层，实现工作流模型解析、任务与 DAG 校验、命令/超时/重试参数校验，以及任务批次的读写路径冲突检测。","obligation_ids":[],"read_roots":["."],"status":"open","step_id":"S1","step_revision":1,"success_evidence":["项目可安装并导入 taskforge；非法任务 ID、依赖、环、命令、超时、attempts 和并发路径冲突均产生明确校验错误。"],"write_roots":["pyproject.toml","taskforge"]}]},{"stage":2,"steps":[{"accepted_evidence_refs":[],"allowed_operations":[],"constraints":["事件历史不可更新或删除；投影必须可由事件历史重建；持久化接口需支持崩溃恢复所需的幂等状态判断。"],"depends_on":["S1"],"objective":"实现 SQLite append-only 事件存储、事件链完整性校验、当前投影、投影重建和原子状态提交接口，记录运行与每次尝试的完整审计字段。","obligation_ids":[],"read_roots":["taskforge"],"status":"open","step_id":"S2","step_revision":1,"success_evidence":["可创建 SQLite 数据库、追加带链校验的运行和尝试事件、重建投影，并在事件被篡改时报告完整性错误。"],"write_roots":["taskforge"]}]},{"stage":3,"steps":[{"accepted_evidence_refs":[],"allowed_operations":[],"constraints":["不得吞掉执行异常；命令启动目录和可写范围必须受 workspace 与任务声明约束；每次尝试保存 command、时间、exit code、stdout、stderr、attempt、输入摘要和输出摘要。"],"depends_on":["S2"],"objective":"实现工作流执行器和恢复逻辑：按 DAG 调度无冲突任务并发执行，限制所有外部副作用在 workspace，处理超时、重试、独立分支失败、最终状态判定、成功任务跳过，以及完成任务后状态提交前崩溃的幂等恢复。","obligation_ids":[],"read_roots":["taskforge"],"status":"open","step_id":"S3","step_revision":1,"success_evidence":["执行器能从持久化投影恢复并继续运行；成功任务不重复执行；失败任务按 max_attempts 重试且不阻塞无关任务；部分完成不会被标记为 succeeded。"],"write_roots":["taskforge"]}]},{"stage":4,"steps":[{"accepted_evidence_refs":[],"allowed_operations":[],"constraints":["CLI 不得绕过领域校验、事件存储或执行器；错误信息不得把失败或中断报告为成功。"],"depends_on":["S3"],"objective":"实现 CLI 命令和应用服务：init、submit、run、status --json、resume，以及投影重建和事件链验证命令；接入 JSON 工作流文件、RUN_ID 和 workspace 参数。","obligation_ids":[],"read_roots":["taskforge","pyproject.toml"],"status":"open","step_id":"S4","step_revision":1,"success_evidence":["CLI 的所有必需命令可执行并返回稳定的成功或错误退出状态；submit 拒绝非法工作流；status 输出当前持久化投影；resume 使用已有运行记录而非重新提交。"],"write_roots":["taskforge","pyproject.toml"]}]},{"stage":5,"steps":[{"accepted_evidence_refs":[],"allowed_operations":[],"constraints":["测试必须验证 SQLite 持久化和事件审计语义，不得只覆盖示例特判；最终验证应运行全部测试及 CLI 验证/重建命令。"],"depends_on":["S4"],"objective":"编写完整测试、示例工作流和 README，覆盖正常 DAG、循环与缺失依赖、并发安全与路径冲突、timeout、retry、中断恢复、成功任务去重、投影重建和篡改检测，并完成全套验证。","obligation_ids":[],"read_roots":["taskforge","tests","examples","pyproject.toml"],"status":"open","step_id":"S5","step_revision":1,"success_evidence":["完整测试套件通过；README 包含架构、关键不变量、安装和验证命令；示例工作流可通过 CLI 提交并运行。"],"write_roots":["tests","examples","README.md"]}]}]`。

## State、工具与协议

- Selector 决策 27 次；后续 parent State 26/26 连续匹配。
- 完整工具描述 27/27；GoalFrontierStateV1 27/27。
- Selector 操作分布：`{"list_directory":20,"move_file":7}`。
- Executor 动作 26 次：`{"list_directory":20,"move_file":6}`；协议拒绝 187 次。
- Step Auditor 接受 23/26 条审计记录；协议拒绝 3 次。
- G1J 输入 Tool Call JSON 锚点 239/239；混入 `Assistant: ```json` 标记 0 次。

## 独立黑盒失败项

- `command_exit`：`{"actual_exit_code":1,"argv":["/opt/verifier-python/bin/python3.13","-c","import importlib\nimport os\nimport subprocess\nimport sys\nimport tomllib\nfrom pathlib import Path\n\nroot = Path.cwd().resolve()\npyproject = root / \"pyproject.toml\"\nreadmes = sorted(root.glob(\"README*\"))\nassert pyproject.is_file(), \"pyproject.toml is required\"\nassert readmes and readmes[0].is_file(), \"README is required\"\nassert (root / 'taskforge').is_dir(), \"import package directory is required\"\ntest_files = sorted((root / \"tests\").rglob(\"test_*.py\"))\nassert test_files, \"tests are required\"\ntest_source = \"\\n\".join(\n    path.read_text(encoding=\"utf-8\", errors=\"replace\")\n    for path `
- `command_exit`：`{"actual_exit_code":1,"argv":["/opt/verifier-python/bin/python3.13","-m","pytest","-q"],"output":"/opt/verifier-python/bin/python3.13: No module named pytest\n","target_exit_code":0}`
- `command_exit`：`{"actual_exit_code":1,"argv":["/opt/verifier-python/bin/python3.13","-c","import json, os, re, subprocess, sys, tempfile, tomllib\nfrom pathlib import Path\nroot=Path.cwd().resolve()\ntarget=tomllib.loads((root/'pyproject.toml').read_text())['project']['scripts']['taskforge']\nmodule_name,function_name=target.split(':',1)\nlauncher=(\"import importlib; m=importlib.import_module(\"+repr(module_name)+\"); f=m; \"\n          \"\\nfor n in \"+repr(function_name.split('.'))+\": f=getattr(f,n)\\nf()\")\nenv=dict(os.environ); env['PYTHONPATH']=str(root)\ndef run(cwd,*args):\n    return subprocess.run([sys.executable,'-c',launcher,*args],cwd=cwd,env=env,\n                          text=True,capture_`
- `event_min_count`：`{"actual":0,"event_type":"attempt_started","minimum":1}`
- `post_effect_crash_resumed`：`{"observed":false}`

## 归因边界

只有无 Supervisor 基础设施失败且至少发生一次 RWKV 请求的轨迹才生成本报告。基础设施无效尝试保留在 `infrastructure_invalid/`，不进入能力分母。

本报告不进行 Head 训练、StateTune、提示词调整、参数调整或验收口径修改。

## 可复核制品

- `P01_S20260903_RESULT.json`
- `P01_S20260903_BASELINE_METRICS.json`
- `P01_S20260903_WORKSPACE_SHA256.json`
- `cases/STRONG-PLANNER-P01-S20260903/audit.json`
- `cases/STRONG-PLANNER-P01-S20260903/causal_ledger.json`
- `cases/STRONG-PLANNER-P01-S20260903/model_trace.json`
- `cases/STRONG-PLANNER-P01-S20260903/event_log.json`
- `cases/STRONG-PLANNER-P01-S20260903/state_timeline.json.gz`
