# P06 run label 20260903 全 zero State 完整项目 Agent 基线

## 结论

- 分类：`valid_zero_state_capability_failure`。
- Goal 终态 `running`，消耗 240 transitions；完整项目未成功。
- 正式轨迹包含 239 次 RWKV 请求和 1 次 Strong 请求。
- 独立黑盒验收 2/7 项通过；最终工作区含 0 个文件或链接。

## Planner 阶段结构

- 计划 revision `1`，共 5 个步骤，完成 0 个。
- 当前阶段：`1`；完成阶段：`[]`。
- 最终 frontier：`["S1"]`。
- 嵌套阶段 JSON：`[{"stage":1,"steps":[{"accepted_evidence_refs":[],"allowed_operations":[],"constraints":["遵循完整需求中的 REST、SQLite、浏览器界面和测试要求","不得使用内存列表作为持久化实现","为后续数据库迁移、API、UI 和测试保留清晰且不冲突的目录边界"],"depends_on":[],"objective":"建立 LocalTrack 的可运行项目骨架，包含后端服务入口、前端资源目录、测试目录、依赖配置和本地启动配置，并明确稳定的模块边界与错误处理约定。","obligation_ids":[],"read_roots":["."],"status":"open","step_id":"S1","step_revision":1,"success_evidence":["项目包含可安装依赖、后端启动入口、前端入口和测试运行入口，且启动命令可执行"],"write_roots":["."]}]},{"stage":2,"steps":[{"accepted_evidence_refs":[],"allowed_operations":[],"constraints":["所有持久化状态必须写入 SQLite","审计日志只能追加不能更新或删除","更新必须校验期望 version 并拒绝静默覆盖"],"depends_on":["S1"],"objective":"实现 SQLite 数据层和可重复执行的自动迁移，覆盖 issue、标签关系、幂等键和 append-only 审计日志，并提供查询、分页、组合过滤及乐观并发所需的数据操作。","obligation_ids":[],"read_roots":["."],"status":"open","step_id":"S2","step_revision":1,"success_evidence":["迁移可重复执行且数据库结构完整；数据层测试证明 CRUD、组合过滤、分页、版本冲突、幂等记录和审计追加均有效"],"write_roots":["."]}]},{"stage":3,"steps":[{"accepted_evidence_refs":[],"allowed_operations":[],"constraints":["所有用户输入必须经过校验和安全处理","API 不得绕过 SQLite 数据层","冲突必须返回明确的结构化响应且不得覆盖已有修改"],"depends_on":["S2"],"objective":"实现稳定 JSON schema 的 REST API，覆盖创建、查看、编辑、关闭、重新打开、删除、搜索过滤分页、审计历史、健康检查和结构化错误响应，并接入 idempotency key 与 optimistic concurrency。","obligation_ids":[],"read_roots":["."],"status":"open","step_id":"S3","step_revision":1,"success_evidence":["API 集成测试验证成功及错误 HTTP 状态码、稳定响应结构、过滤分页、幂等创建、版本冲突、审计记录和健康检查"],"write_roots":["."]}]},{"stage":4,"steps":[{"accepted_evidence_refs":[],"allowed_operations":[],"constraints":["不得制作静态演示页面或使用前端内存冒充持久化","必须调用真实 REST API","显示用户内容时必须安全转义"],"depends_on":["S3"],"objective":"实现浏览器界面并完成真实 API 联调，提供 Issue 列表、组合筛选、分页、新建、编辑、关闭、重新打开、删除、冲突提示和审计历史，确保刷新后从服务端恢复状态并安全转义用户输入。","obligation_ids":[],"read_roots":["."],"status":"open","step_id":"S4","step_revision":1,"success_evidence":["浏览器级测试通过列表、筛选、新建、编辑、状态切换、冲突提示、审计历史和刷新持久化流程"],"write_roots":["."]}]},{"stage":5,"steps":[{"accepted_evidence_refs":[],"allowed_operations":[],"constraints":["测试必须覆盖数据库迁移、并发冲突、幂等创建、审计日志和真实 UI 联调","最终验证不得以 API 测试替代浏览器端到端测试","备份和恢复说明必须对应实际数据库文件与运行方式"],"depends_on":["S4"],"objective":"补齐单元测试、API 集成测试、迁移测试和至少一个浏览器端到端测试，编写包含安装、启动、测试、备份和恢复的 README，实际启动服务并执行健康检查与端到端验证。","obligation_ids":[],"read_roots":["."],"status":"open","step_id":"S5","step_revision":1,"success_evidence":["完整测试命令通过；服务实际启动；健康检查成功；浏览器端到端测试成功；README 包含安装、启动、测试、备份和恢复步骤"],"write_roots":["."]}]}]`。

## State、工具与协议

- Selector 决策 56 次；后续 parent State 55/55 连续匹配。
- 完整工具描述 56/56；GoalFrontierStateV1 56/56。
- Selector 操作分布：`{"list_directory":39,"move_file":17}`。
- Executor 动作 55 次：`{"list_directory":38,"move_file":17}`；协议拒绝 129 次。
- Step Auditor 接受 54/55 条审计记录；协议拒绝 1 次。
- G1J 输入 Tool Call JSON 锚点 239/239；混入 `Assistant: ```json` 标记 0 次。

## 独立黑盒失败项

- `command_exit`：`{"actual_exit_code":1,"argv":["/opt/verifier-python/bin/python3.13","-c","import importlib\nimport os\nimport subprocess\nimport sys\nimport tomllib\nfrom pathlib import Path\n\nroot = Path.cwd().resolve()\npyproject = root / \"pyproject.toml\"\nreadmes = sorted(root.glob(\"README*\"))\nassert pyproject.is_file(), \"pyproject.toml is required\"\nassert readmes and readmes[0].is_file(), \"README is required\"\nassert (root / 'localtrack').is_dir(), \"import package directory is required\"\ntest_files = sorted((root / \"tests\").rglob(\"test_*.py\"))\nassert test_files, \"tests are required\"\ntest_source = \"\\n\".join(\n    path.read_text(encoding=\"utf-8\", errors=\"replace\")\n    for path`
- `command_exit`：`{"actual_exit_code":1,"argv":["/opt/verifier-python/bin/python3.13","-m","pytest","-q"],"output":"/opt/verifier-python/bin/python3.13: No module named pytest\n","target_exit_code":0}`
- `command_exit`：`{"actual_exit_code":1,"argv":["/opt/verifier-python/bin/python3.13","-c","from pathlib import Path\nroot=Path.cwd().resolve()\nweb_files=[p for p in root.rglob('*') if p.is_file() and p.suffix.lower() in {'.html','.js','.css'}]\nassert any(p.suffix.lower()=='.html' for p in web_files), 'browser UI HTML is missing'\nbrowser_tests=[p for p in root.rglob('*') if p.is_file() and (\n    any(marker in p.name.lower() for marker in ('e2e','browser','playwright','selenium','test_ui'))\n    or (p.suffix.lower()=='.js' and 'test' in p.name.lower())\n)]\nassert browser_tests, 'browser-level end-to-end test is missing'\ncorpus='\\n'.join(p.read_text(encoding='utf-8',errors='replace') for p in sorted(root`
- `event_min_count`：`{"actual":0,"event_type":"attempt_started","minimum":1}`
- `post_effect_crash_resumed`：`{"observed":false}`

## 归因边界

只有无 Supervisor 基础设施失败且至少发生一次 RWKV 请求的轨迹才生成本报告。基础设施无效尝试保留在 `infrastructure_invalid/`，不进入能力分母。

本报告不进行 Head 训练、StateTune、提示词调整、参数调整或验收口径修改。

## 可复核制品

- `P06_S20260903_RESULT.json`
- `P06_S20260903_BASELINE_METRICS.json`
- `P06_S20260903_WORKSPACE_SHA256.json`
- `cases/STRONG-PLANNER-P06-S20260903/audit.json`
- `cases/STRONG-PLANNER-P06-S20260903/causal_ledger.json`
- `cases/STRONG-PLANNER-P06-S20260903/model_trace.json`
- `cases/STRONG-PLANNER-P06-S20260903/event_log.json`
- `cases/STRONG-PLANNER-P06-S20260903/state_timeline.json.gz`
