# P02 run label 20260903 全 zero State 完整项目 Agent 基线

## 结论

- 分类：`valid_zero_state_capability_failure`。
- Goal 终态 `running`，消耗 240 transitions；完整项目未成功。
- 正式轨迹包含 239 次 RWKV 请求和 1 次 Strong 请求。
- 独立黑盒验收 2/7 项通过；最终工作区含 0 个文件或链接。

## Planner 阶段结构

- 计划 revision `1`，共 5 个步骤，完成 0 个。
- 当前阶段：`1`；完成阶段：`[]`。
- 最终 frontier：`["S1"]`。
- 嵌套阶段 JSON：`[{"stage":1,"steps":[{"accepted_evidence_refs":[],"allowed_operations":[],"constraints":["先确认工作区为空且不存在可复用的规范或验证器；不得依赖外部路径"],"depends_on":[],"objective":"检查空工作区并建立 ConfigMigrate 的 Python 包、CLI 入口、测试目录和基础项目元数据，明确配置格式、迁移接口与事务数据模型","obligation_ids":[],"read_roots":["."],"status":"open","step_id":"S1","step_revision":1,"success_evidence":["项目包含可安装的 ConfigMigrate 包、CLI 入口和可运行的基础测试命令"],"write_roots":["."]}]},{"stage":2,"steps":[{"accepted_evidence_refs":[],"allowed_operations":[],"constraints":["plan 相关逻辑必须只读；迁移不得删除未声明字段"],"depends_on":["S1"],"objective":"实现 JSON 配置发现、解析校验、连续版本迁移链、v1 到 v2 到 v3 示例迁移、未知字段保留和幂等迁移逻辑","obligation_ids":[],"read_roots":["."],"status":"open","step_id":"S2","step_revision":1,"success_evidence":["单元测试覆盖嵌套目录、空目录、非法 JSON、未知版本、不连续迁移链、未知字段保留和重复迁移幂等性"],"write_roots":["."]}]},{"stage":3,"steps":[{"accepted_evidence_refs":[],"allowed_operations":[],"constraints":["任一文件失败必须 fail-closed；不得静默继续；所有配置写入必须经过同目录临时文件、fsync 和原子替换"],"depends_on":["S2"],"objective":"实现事务 manifest、状态机、同目录临时文件写入、fsync、原子替换、外部修改检测、提交边界恢复和完整回滚机制","obligation_ids":[],"read_roots":["."],"status":"open","step_id":"S3","step_revision":1,"success_evidence":["测试可观察到原始 SHA-256、目标 SHA-256、路径、迁移链和事务 ID 被持久化，并验证失败、崩溃、resume 和 rollback 均保持明确可判定状态"],"write_roots":["."]}]},{"stage":4,"steps":[{"accepted_evidence_refs":[],"allowed_operations":[],"constraints":["支持目标版本参数和事务 ID；命令失败时返回非零状态并保留可恢复事务信息"],"depends_on":["S3"],"objective":"完成 inspect、plan、apply、resume、rollback、verify 六个 CLI 命令及参数校验、错误输出和事务状态展示","obligation_ids":[],"read_roots":["."],"status":"open","step_id":"S4","step_revision":1,"success_evidence":["CLI 帮助和六个命令均可执行，plan 不修改文件，apply/resume/rollback/verify 与事务引擎行为一致"],"write_roots":["."]}]},{"stage":5,"steps":[{"accepted_evidence_refs":[],"allowed_operations":[],"constraints":["演示必须使用真实生成的配置文件和事务状态；不得只用伪造输出替代执行结果"],"depends_on":["S4"],"objective":"补齐全量集成测试、不同提交位置的进程崩溃模拟、真实 apply/resume/rollback 演示脚本，并编写 README 说明状态机、恢复语义和文件安全边界","obligation_ids":[],"read_roots":["."],"status":"open","step_id":"S5","step_revision":1,"success_evidence":["全量测试通过，README 包含要求的安全与恢复说明，并有一次可复现的 apply、中断恢复和 rollback 演示输出"],"write_roots":["."]}]}]`。

## State、工具与协议

- Selector 决策 56 次；后续 parent State 55/55 连续匹配。
- 完整工具描述 56/56；GoalFrontierStateV1 56/56。
- Selector 操作分布：`{"list_directory":49,"move_file":7}`。
- Executor 动作 55 次：`{"list_directory":48,"move_file":7}`；协议拒绝 129 次。
- Step Auditor 接受 52/55 条审计记录；协议拒绝 3 次。
- G1J 输入 Tool Call JSON 锚点 239/239；混入 `Assistant: ```json` 标记 0 次。

## 独立黑盒失败项

- `command_exit`：`{"actual_exit_code":1,"argv":["/opt/verifier-python/bin/python3.13","-c","import importlib\nimport os\nimport subprocess\nimport sys\nimport tomllib\nfrom pathlib import Path\n\nroot = Path.cwd().resolve()\npyproject = root / \"pyproject.toml\"\nreadmes = sorted(root.glob(\"README*\"))\nassert pyproject.is_file(), \"pyproject.toml is required\"\nassert readmes and readmes[0].is_file(), \"README is required\"\nassert (root / 'configmigrate').is_dir(), \"import package directory is required\"\ntest_files = sorted((root / \"tests\").rglob(\"test_*.py\"))\nassert test_files, \"tests are required\"\ntest_source = \"\\n\".join(\n    path.read_text(encoding=\"utf-8\", errors=\"replace\")\n    for p`
- `command_exit`：`{"actual_exit_code":1,"argv":["/opt/verifier-python/bin/python3.13","-m","pytest","-q"],"output":"/opt/verifier-python/bin/python3.13: No module named pytest\n","target_exit_code":0}`
- `command_exit`：`{"actual_exit_code":1,"argv":["/opt/verifier-python/bin/python3.13","-c","import os, subprocess, sys, tempfile, tomllib\nfrom pathlib import Path\nroot=Path.cwd().resolve()\ntarget=tomllib.loads((root/'pyproject.toml').read_text())['project']['scripts']['configmigrate']\nmodule_name,function_name=target.split(':',1)\nlauncher=(\"import importlib; m=importlib.import_module(\"+repr(module_name)+\"); f=m; \"\n          \"\\nfor n in \"+repr(function_name.split('.'))+\": f=getattr(f,n)\\nf()\")\nenv=dict(os.environ); env['PYTHONPATH']=str(root)\nwith tempfile.TemporaryDirectory() as d:\n    bad=Path(d)/'bad.json'; bad.write_text('{invalid',encoding='utf-8')\n    before=bad.read_bytes()\n    r=su`
- `event_min_count`：`{"actual":0,"event_type":"attempt_started","minimum":1}`
- `post_effect_crash_resumed`：`{"observed":false}`

## 归因边界

只有无 Supervisor 基础设施失败且至少发生一次 RWKV 请求的轨迹才生成本报告。基础设施无效尝试保留在 `infrastructure_invalid/`，不进入能力分母。

本报告不进行 Head 训练、StateTune、提示词调整、参数调整或验收口径修改。

## 可复核制品

- `P02_S20260903_RESULT.json`
- `P02_S20260903_BASELINE_METRICS.json`
- `P02_S20260903_WORKSPACE_SHA256.json`
- `cases/STRONG-PLANNER-P02-S20260903/audit.json`
- `cases/STRONG-PLANNER-P02-S20260903/causal_ledger.json`
- `cases/STRONG-PLANNER-P02-S20260903/model_trace.json`
- `cases/STRONG-PLANNER-P02-S20260903/event_log.json`
- `cases/STRONG-PLANNER-P02-S20260903/state_timeline.json.gz`
