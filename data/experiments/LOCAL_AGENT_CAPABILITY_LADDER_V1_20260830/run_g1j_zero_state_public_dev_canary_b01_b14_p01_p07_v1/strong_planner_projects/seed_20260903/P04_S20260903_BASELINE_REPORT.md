# P04 run label 20260903 全 zero State 完整项目 Agent 基线

## 结论

- 分类：`valid_zero_state_capability_failure`。
- Goal 终态 `running`，消耗 240 transitions；完整项目未成功。
- 正式轨迹包含 239 次 RWKV 请求和 1 次 Strong 请求。
- 独立黑盒验收 2/7 项通过；最终工作区含 0 个文件或链接。

## Planner 阶段结构

- 计划 revision `1`，共 5 个步骤，完成 0 个。
- 当前阶段：`1`；完成阶段：`[]`。
- 最终 frontier：`["S1"]`。
- 嵌套阶段 JSON：`[{"stage":1,"steps":[{"accepted_evidence_refs":[],"allowed_operations":[],"constraints":["先完成规范和验证入口检查，再进行任何文件创建"],"depends_on":[],"objective":"检查空工作区及可用规范或验证入口，并整理 RepoGraph 的实现与验收约束","obligation_ids":[],"read_roots":["."],"status":"open","step_id":"S1","step_revision":1,"success_evidence":["已记录工作区内容、可用验证入口以及需求对应的验收清单"],"write_roots":[]}]},{"stage":2,"steps":[{"accepted_evidence_refs":[],"allowed_operations":[],"constraints":["保持目录和模块职责清晰","为 SQLite 或内容寻址缓存、诊断、确定性输出预留接口"],"depends_on":["S1"],"objective":"创建 RepoGraph 的 Python 项目骨架、命令行入口、持久化数据模型、示例仓库和测试目录结构","obligation_ids":[],"read_roots":["."],"status":"open","step_id":"S2","step_revision":1,"success_evidence":["项目元数据、源码包、测试目录、示例仓库和基础命令入口均已创建并可被 Python 导入"],"write_roots":["pyproject.toml","repograph","tests","examples"]}]},{"stage":3,"steps":[{"accepted_evidence_refs":[],"allowed_operations":[],"constraints":["不得使用正则表达式替代 AST 分析","相对导入必须按包语义解析","无法静态确认的调用只能标记 unresolved"],"depends_on":["S2"],"objective":"实现基于 Python AST 的项目扫描、相对导入解析、符号与关系建模、语法错误诊断、未解析动态调用标记、增量缓存及陈旧节点清理","obligation_ids":[],"read_roots":["repograph","examples"],"status":"open","step_id":"S3","step_revision":1,"success_evidence":["扫描结果包含模块、导入与别名、类继承、函数或方法定义、可确认调用、测试引用和 unresolved 风险，且未变化文件不会重新解析、删除或重命名文件不会保留节点"],"write_roots":["repograph"]}]},{"stage":4,"steps":[{"accepted_evidence_refs":[],"allowed_operations":[],"constraints":["循环检测输出确定性最小环","重复扫描和报告生成结果必须一致","report --json 必须写出有效 JSON"],"depends_on":["S3"],"objective":"实现全部 repograph 命令、符号查询、依赖与反向依赖、影响分析、确定性最小环检测及 JSON 报告输出","obligation_ids":[],"read_roots":["repograph","examples"],"status":"open","step_id":"S4","step_revision":1,"success_evidence":["scan、symbol、dependencies、dependents、impact、cycles 和 report --json 均可运行，并按稳定顺序输出 direct dependents、transitive dependents、affected tests 和 unresolved risks"],"write_roots":["repograph"]}]},{"stage":5,"steps":[{"accepted_evidence_refs":[],"allowed_operations":[],"constraints":["覆盖相对导入、alias、继承、循环、动态导入、测试引用、语法错误、删除或重命名和确定性输出"],"depends_on":["S4"],"objective":"补充完整单元测试、集成测试和性能测试，验证示例仓库场景及单文件修改时的局部重算，并对 RepoGraph 自身执行扫描生成真实影响报告","obligation_ids":[],"read_roots":["repograph","tests","examples"],"status":"open","step_id":"S5","step_revision":1,"success_evidence":["测试套件通过，性能测试证明单文件修改只重算相关部分，且 RepoGraph 已成功扫描自身并生成真实 JSON 影响分析报告"],"write_roots":["tests","reports"]}]}]`。

## State、工具与协议

- Selector 决策 65 次；后续 parent State 64/64 连续匹配。
- 完整工具描述 65/65；GoalFrontierStateV1 65/65。
- Selector 操作分布：`{"list_directory":65}`。
- Executor 动作 64 次：`{"list_directory":64}`；协议拒绝 111 次。
- Step Auditor 接受 61/64 条审计记录；协议拒绝 3 次。
- G1J 输入 Tool Call JSON 锚点 239/239；混入 `Assistant: ```json` 标记 0 次。

## 独立黑盒失败项

- `command_exit`：`{"actual_exit_code":1,"argv":["/opt/verifier-python/bin/python3.13","-c","import importlib\nimport os\nimport subprocess\nimport sys\nimport tomllib\nfrom pathlib import Path\n\nroot = Path.cwd().resolve()\npyproject = root / \"pyproject.toml\"\nreadmes = sorted(root.glob(\"README*\"))\nassert pyproject.is_file(), \"pyproject.toml is required\"\nassert readmes and readmes[0].is_file(), \"README is required\"\nassert (root / 'repograph').is_dir(), \"import package directory is required\"\ntest_files = sorted((root / \"tests\").rglob(\"test_*.py\"))\nassert test_files, \"tests are required\"\ntest_source = \"\\n\".join(\n    path.read_text(encoding=\"utf-8\", errors=\"replace\")\n    for path `
- `command_exit`：`{"actual_exit_code":1,"argv":["/opt/verifier-python/bin/python3.13","-m","pytest","-q"],"output":"/opt/verifier-python/bin/python3.13: No module named pytest\n","target_exit_code":0}`
- `command_exit`：`{"actual_exit_code":1,"argv":["/opt/verifier-python/bin/python3.13","-c","import json, os, subprocess, sys, tempfile, tomllib\nfrom pathlib import Path\nroot=Path.cwd().resolve()\ntarget=tomllib.loads((root/'pyproject.toml').read_text())['project']['scripts']['repograph']\nmodule_name,function_name=target.split(':',1)\nlauncher=(\"import importlib; m=importlib.import_module(\"+repr(module_name)+\"); f=m; \"\n          \"\\nfor n in \"+repr(function_name.split('.'))+\": f=getattr(f,n)\\nf()\")\nenv=dict(os.environ); env['PYTHONPATH']=str(root)\ndef run(cwd,*args):\n    return subprocess.run([sys.executable,'-c',launcher,*args],cwd=cwd,env=env,\n                          text=True,capture_outp`
- `event_min_count`：`{"actual":0,"event_type":"attempt_started","minimum":1}`
- `post_effect_crash_resumed`：`{"observed":false}`

## 归因边界

只有无 Supervisor 基础设施失败且至少发生一次 RWKV 请求的轨迹才生成本报告。基础设施无效尝试保留在 `infrastructure_invalid/`，不进入能力分母。

本报告不进行 Head 训练、StateTune、提示词调整、参数调整或验收口径修改。

## 可复核制品

- `P04_S20260903_RESULT.json`
- `P04_S20260903_BASELINE_METRICS.json`
- `P04_S20260903_WORKSPACE_SHA256.json`
- `cases/STRONG-PLANNER-P04-S20260903/audit.json`
- `cases/STRONG-PLANNER-P04-S20260903/causal_ledger.json`
- `cases/STRONG-PLANNER-P04-S20260903/model_trace.json`
- `cases/STRONG-PLANNER-P04-S20260903/event_log.json`
- `cases/STRONG-PLANNER-P04-S20260903/state_timeline.json.gz`
