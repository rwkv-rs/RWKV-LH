# P05 run label 20260903 全 zero State 完整项目 Agent 基线

## 结论

- 分类：`valid_zero_state_capability_failure`。
- Goal 终态 `running`，消耗 240 transitions；完整项目未成功。
- 正式轨迹包含 239 次 RWKV 请求和 1 次 Strong 请求。
- 独立黑盒验收 2/7 项通过；最终工作区含 0 个文件或链接。

## Planner 阶段结构

- 计划 revision `1`，共 5 个步骤，完成 0 个。
- 当前阶段：`1`；完成阶段：`[]`。
- 最终 frontier：`["S1"]`。
- 嵌套阶段 JSON：`[{"stage":1,"steps":[{"accepted_evidence_refs":[],"allowed_operations":[],"constraints":["先以当前需求作为规格依据；不得跟随符号链接；所有持久状态必须位于项目配置的同步工作区内"],"depends_on":[],"objective":"根据需求建立 SyncLedger Python 包骨架、持久化模型、路径安全与符号链接处理基础，并定义 manifest、tombstone、计划和审计记录的数据结构","obligation_ids":[],"read_roots":["."],"status":"open","step_id":"S1","step_revision":1,"success_evidence":["包结构、项目元数据和可序列化的数据模型已创建，基础路径校验与 SHA-256 计算可被测试调用"],"write_roots":["pyproject.toml","syncledger"]}]},{"stage":2,"steps":[{"accepted_evidence_refs":[],"allowed_operations":[],"constraints":["plan 必须基于 SHA-256、大小、修改元数据和持久 manifest；删除必须通过 tombstone 表达；路径必须保持在对应根目录内"],"depends_on":["S1"],"objective":"实现双目录初始化、只读 plan、基线建立及变更分类逻辑，覆盖新增、修改、删除、相同修改、不同修改、删除与修改冲突、类型冲突和 no-op","obligation_ids":[],"read_roots":["syncledger"],"status":"open","step_id":"S2","step_revision":1,"success_evidence":["plan 不修改文件或持久状态以外的同步状态，并输出明确的 copy、delete、mkdir、conflict、no-op 操作及稳定 PLAN_ID"],"write_roots":["syncledger"]}]},{"stage":3,"steps":[{"accepted_evidence_refs":[],"allowed_operations":[],"constraints":["不得静默覆盖双侧不同修改；apply 必须校验源内容并原子提交；恢复时必须识别已正确提交的操作"],"depends_on":["S2"],"objective":"实现 apply、resume、status、conflicts 和 CLI 命令，加入过期计划拒绝、临时文件校验、原子替换、幂等提交、中断恢复及 append-only 审计","obligation_ids":[],"read_roots":["syncledger","pyproject.toml"],"status":"open","step_id":"S3","step_revision":1,"success_evidence":["CLI 支持全部要求的子命令；过期源文件会拒绝 apply；重复 apply 和 resume 不会重复破坏性操作；每个操作均产生可查询审计记录"],"write_roots":["syncledger"]}]},{"stage":4,"steps":[{"accepted_evidence_refs":[],"allowed_operations":[],"constraints":["测试必须使用临时目录并验证 plan 只读；忽略匹配语义必须有正向和反向断言"],"depends_on":["S3"],"objective":"建立自动化测试，覆盖冲突检测、删除传播、过期计划、中断恢复、符号链接与路径逃逸防护、忽略规则、幂等重复 apply、manifest 和审计持久化","obligation_ids":[],"read_roots":["syncledger","pyproject.toml"],"status":"open","step_id":"S4","step_revision":1,"success_evidence":["测试套件可执行并覆盖所有列出的场景，关键失败路径明确断言冲突、拒绝或安全错误"],"write_roots":["tests"]}]},{"stage":5,"steps":[{"accepted_evidence_refs":[],"allowed_operations":[],"constraints":["演示不得依赖绝对路径或外部服务；示例状态和审计记录应可重复清理并重新运行"],"depends_on":["S4"],"objective":"创建两个示例目录并运行真实演示，记录正常同步、冲突检测和中断恢复的可复现步骤与结果","obligation_ids":[],"read_roots":["syncledger","tests"],"status":"open","step_id":"S5","step_revision":1,"success_evidence":["示例目录、演示脚本或文档已生成，实际运行结果展示正常同步、冲突保留以及恢复后无重复破坏性操作"],"write_roots":["examples"]}]}]`。

## State、工具与协议

- Selector 决策 59 次；后续 parent State 58/58 连续匹配。
- 完整工具描述 59/59；GoalFrontierStateV1 59/59。
- Selector 操作分布：`{"list_directory":53,"move_file":6}`。
- Executor 动作 58 次：`{"list_directory":52,"move_file":6}`；协议拒绝 123 次。
- Step Auditor 接受 56/58 条审计记录；协议拒绝 2 次。
- G1J 输入 Tool Call JSON 锚点 239/239；混入 `Assistant: ```json` 标记 0 次。

## 独立黑盒失败项

- `command_exit`：`{"actual_exit_code":1,"argv":["/opt/verifier-python/bin/python3.13","-c","import importlib\nimport os\nimport subprocess\nimport sys\nimport tomllib\nfrom pathlib import Path\n\nroot = Path.cwd().resolve()\npyproject = root / \"pyproject.toml\"\nreadmes = sorted(root.glob(\"README*\"))\nassert pyproject.is_file(), \"pyproject.toml is required\"\nassert readmes and readmes[0].is_file(), \"README is required\"\nassert (root / 'syncledger').is_dir(), \"import package directory is required\"\ntest_files = sorted((root / \"tests\").rglob(\"test_*.py\"))\nassert test_files, \"tests are required\"\ntest_source = \"\\n\".join(\n    path.read_text(encoding=\"utf-8\", errors=\"replace\")\n    for path`
- `command_exit`：`{"actual_exit_code":1,"argv":["/opt/verifier-python/bin/python3.13","-m","pytest","-q"],"output":"/opt/verifier-python/bin/python3.13: No module named pytest\n","target_exit_code":0}`
- `command_exit`：`{"actual_exit_code":1,"argv":["/opt/verifier-python/bin/python3.13","-c","import hashlib, os, subprocess, sys, tempfile, tomllib\nfrom pathlib import Path\nroot=Path.cwd().resolve()\ntarget=tomllib.loads((root/'pyproject.toml').read_text())['project']['scripts']['syncledger']\nmodule_name,function_name=target.split(':',1)\nlauncher=(\"import importlib; m=importlib.import_module(\"+repr(module_name)+\"); f=m; \"\n          \"\\nfor n in \"+repr(function_name.split('.'))+\": f=getattr(f,n)\\nf()\")\nenv=dict(os.environ); env['PYTHONPATH']=str(root)\ndef run(cwd,*args):\n    return subprocess.run([sys.executable,'-c',launcher,*args],cwd=cwd,env=env,\n                          text=True,capture_`
- `event_min_count`：`{"actual":0,"event_type":"attempt_started","minimum":1}`
- `post_effect_crash_resumed`：`{"observed":false}`

## 归因边界

只有无 Supervisor 基础设施失败且至少发生一次 RWKV 请求的轨迹才生成本报告。基础设施无效尝试保留在 `infrastructure_invalid/`，不进入能力分母。

本报告不进行 Head 训练、StateTune、提示词调整、参数调整或验收口径修改。

## 可复核制品

- `P05_S20260903_RESULT.json`
- `P05_S20260903_BASELINE_METRICS.json`
- `P05_S20260903_WORKSPACE_SHA256.json`
- `cases/STRONG-PLANNER-P05-S20260903/audit.json`
- `cases/STRONG-PLANNER-P05-S20260903/causal_ledger.json`
- `cases/STRONG-PLANNER-P05-S20260903/model_trace.json`
- `cases/STRONG-PLANNER-P05-S20260903/event_log.json`
- `cases/STRONG-PLANNER-P05-S20260903/state_timeline.json.gz`
