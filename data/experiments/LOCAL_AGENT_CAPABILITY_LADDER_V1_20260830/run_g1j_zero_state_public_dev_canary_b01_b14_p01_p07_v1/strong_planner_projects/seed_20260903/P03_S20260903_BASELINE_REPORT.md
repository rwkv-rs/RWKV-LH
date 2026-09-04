# P03 run label 20260903 全 zero State 完整项目 Agent 基线

## 结论

- 分类：`valid_zero_state_capability_failure`。
- Goal 终态 `running`，消耗 240 transitions；完整项目未成功。
- 正式轨迹包含 239 次 RWKV 请求和 1 次 Strong 请求。
- 独立黑盒验收 2/7 项通过；最终工作区含 0 个文件或链接。

## Planner 阶段结构

- 计划 revision `1`，共 5 个步骤，完成 0 个。
- 当前阶段：`1`；完成阶段：`[]`。
- 最终 frontier：`["S1"]`。
- 嵌套阶段 JSON：`[{"stage":1,"steps":[{"accepted_evidence_refs":[],"allowed_operations":[],"constraints":["实现必须使用持久化 SQLite 状态，不得依赖全局内存锁；为后续实现保留事件日志、幂等记录、投影和哈希链所需结构"],"depends_on":[],"objective":"检查空项目并建立 LedgerStock 的 Python 包、SQLite 持久化基础、CLI 入口及可执行的验收测试骨架，明确事件、幂等请求、投影和校验所需的数据模型与事务边界","obligation_ids":[],"read_roots":["."],"status":"open","step_id":"S1","step_revision":1,"success_evidence":["项目包含可导入的 LedgerStock 包、CLI 入口、SQLite schema 初始化逻辑和可运行的测试入口"],"write_roots":["."]}]},{"stage":2,"steps":[{"accepted_evidence_refs":[],"allowed_operations":[],"constraints":["所有修改命令必须要求全局唯一 idempotency_key；reserve 必须在数据库事务和锁策略下防止超卖；不得使用全局内存锁掩盖持久化一致性问题"],"depends_on":["S1"],"objective":"实现事件追加、全局幂等键处理、库存领域操作及基于 SQLite 事务的并发安全写入，覆盖 receive、reserve、release、ship、adjust 的不变量和中断恢复语义","obligation_ids":[],"read_roots":["."],"status":"open","step_id":"S2","step_revision":1,"success_evidence":["领域服务能够在事务中追加事件并更新幂等结果；重复相同 payload 返回原结果；相同 key 的不同 payload 被拒绝；非法库存变化被拒绝"],"write_roots":["."]}]},{"stage":3,"steps":[{"accepted_evidence_refs":[],"allowed_operations":[],"constraints":["当前库存必须由事件重放得到；校验不得仅依赖投影；输出同时支持机器可读 JSON 和人类可读格式"],"depends_on":["S2"],"objective":"实现事件投影读取、投影删除与完整重建、指定时间点库存历史查询、事件历史展示和 ledger 哈希链校验，并完成全部 CLI 命令的 JSON 与人类可读输出","obligation_ids":[],"read_roots":["."],"status":"open","step_id":"S3","step_revision":1,"success_evidence":["CLI 支持全部九个命令；删除投影后 rebuild-projection 恢复相同状态；历史查询按时间点重放事件；verify-ledger 能报告顺序、内容或缺失篡改"],"write_roots":["."]}]},{"stage":4,"steps":[{"accepted_evidence_refs":[],"allowed_operations":[],"constraints":["并发测试必须使用真实独立数据库连接或进程；不得通过测试专用全局锁规避竞态；篡改测试必须验证 ledger 校验失败"],"depends_on":["S3"],"objective":"补齐端到端和并发测试，覆盖正常流程、超卖、重复请求、幂等冲突、并发 reserve、投影重建、ledger 篡改、历史时间点查询、SQLite 锁冲突及进程中断恢复","obligation_ids":[],"read_roots":["."],"status":"open","step_id":"S4","step_revision":1,"success_evidence":["测试套件包含所有指定场景，并能稳定验证重复请求不重复写事件、并发 reserve 不超卖以及中断后无双重扣减"],"write_roots":["."]}]},{"stage":5,"steps":[{"accepted_evidence_refs":[],"allowed_operations":[],"constraints":["不得删除覆盖需求的测试；最终实现必须保持 append-only 事件日志并能从日志重建投影"],"depends_on":["S4"],"objective":"运行完整测试和 CLI 验收，修复发现的问题，并补充事务边界、SQLite 并发策略、恢复流程和使用方式文档","obligation_ids":[],"read_roots":["."],"status":"open","step_id":"S5","step_revision":1,"success_evidence":["全部测试通过；CLI 验收命令成功执行；文档明确说明事件追加、幂等检查、投影更新、锁等待和恢复的事务边界与并发策略"],"write_roots":["."]}]}]`。

## State、工具与协议

- Selector 决策 57 次；后续 parent State 56/56 连续匹配。
- 完整工具描述 57/57；GoalFrontierStateV1 57/57。
- Selector 操作分布：`{"list_directory":56,"move_file":1}`。
- Executor 动作 56 次：`{"list_directory":55,"move_file":1}`；协议拒绝 127 次。
- Step Auditor 接受 52/56 条审计记录；协议拒绝 4 次。
- G1J 输入 Tool Call JSON 锚点 239/239；混入 `Assistant: ```json` 标记 0 次。

## 独立黑盒失败项

- `command_exit`：`{"actual_exit_code":1,"argv":["/opt/verifier-python/bin/python3.13","-c","import importlib\nimport os\nimport subprocess\nimport sys\nimport tomllib\nfrom pathlib import Path\n\nroot = Path.cwd().resolve()\npyproject = root / \"pyproject.toml\"\nreadmes = sorted(root.glob(\"README*\"))\nassert pyproject.is_file(), \"pyproject.toml is required\"\nassert readmes and readmes[0].is_file(), \"README is required\"\nassert (root / 'ledgerstock').is_dir(), \"import package directory is required\"\ntest_files = sorted((root / \"tests\").rglob(\"test_*.py\"))\nassert test_files, \"tests are required\"\ntest_source = \"\\n\".join(\n    path.read_text(encoding=\"utf-8\", errors=\"replace\")\n    for pat`
- `command_exit`：`{"actual_exit_code":1,"argv":["/opt/verifier-python/bin/python3.13","-m","pytest","-q"],"output":"/opt/verifier-python/bin/python3.13: No module named pytest\n","target_exit_code":0}`
- `command_exit`：`{"actual_exit_code":1,"argv":["/opt/verifier-python/bin/python3.13","-c","import os, subprocess, sys, tomllib\nfrom pathlib import Path\nroot=Path.cwd().resolve()\ntarget=tomllib.loads((root/'pyproject.toml').read_text())['project']['scripts']['ledgerstock']\nmodule_name,function_name=target.split(':',1)\nlauncher=(\"import importlib; m=importlib.import_module(\"+repr(module_name)+\"); f=m; \"\n          \"\\nfor n in \"+repr(function_name.split('.'))+\": f=getattr(f,n)\\nf()\")\nenv=dict(os.environ); env['PYTHONPATH']=str(root)\ndef help_for(command):\n    return subprocess.run([sys.executable,'-c',launcher,command,'--help'],cwd=root,env=env,\n                          text=True,capture_out`
- `event_min_count`：`{"actual":0,"event_type":"attempt_started","minimum":1}`
- `post_effect_crash_resumed`：`{"observed":false}`

## 归因边界

只有无 Supervisor 基础设施失败且至少发生一次 RWKV 请求的轨迹才生成本报告。基础设施无效尝试保留在 `infrastructure_invalid/`，不进入能力分母。

本报告不进行 Head 训练、StateTune、提示词调整、参数调整或验收口径修改。

## 可复核制品

- `P03_S20260903_RESULT.json`
- `P03_S20260903_BASELINE_METRICS.json`
- `P03_S20260903_WORKSPACE_SHA256.json`
- `cases/STRONG-PLANNER-P03-S20260903/audit.json`
- `cases/STRONG-PLANNER-P03-S20260903/causal_ledger.json`
- `cases/STRONG-PLANNER-P03-S20260903/model_trace.json`
- `cases/STRONG-PLANNER-P03-S20260903/event_log.json`
- `cases/STRONG-PLANNER-P03-S20260903/state_timeline.json.gz`
