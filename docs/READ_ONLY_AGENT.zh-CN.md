# RWKV 文档问答与代码检查入口

本入口使用当前生产 Controller 和唯一输入构造函数。用户提供工作区和问题；RWKV 自主选择只读工具、参数和最终回答。连续调用延续观察 child State，独立任务从 zero State 开始。没有 Planner、逐步强模型审核或预算结束后的强制总结。

```bash
.venv/bin/python scripts/run_rwkv_read_only_agent.py \
  --jobs /absolute/path/jobs.json --concurrency 1 \
  --base-url http://127.0.0.1:29613/v1 \
  --model rwkv7-g1j-13.3b-zero-state-capability-ctx16384 \
  --model-sha256 559371f5b9aef13189ae54b345ac096af4ad2b689996c05d89de687612b3ae65
```

任务文件是独立任务列表；目录必须使用绝对路径，输出目录必须尚不存在且位于模型工作区之外：

```json
[
  {
    "task_id": "document-question",
    "request": "阅读 README.md，说明项目用途和已知限制。只依据实际文件回答。",
    "workspace": "/absolute/path/project",
    "output_dir": "/absolute/path/results/document-question",
    "max_calls": 6,
    "max_seconds": 300
  }
]
```

只读能力按生产工具注册的权限属性公开。模型可搜索、读取并在工具允许的临时工作区视图内检查；不能保留代码修改。此模式用于文档问答和检查，不承担代码修复。不要在同一工作区同时运行外部写任务；这不是文件系统级安全沙箱。

每任务保留 `RESULT.json`（原始 final、提交/预算/错误、调用数）、`MATERIALS.json`（真实工具观察、原文坐标和来源哈希、后续消费请求）、`state_snapshot.json` 和 `model_trace.jsonl`。材料不是程序生成的摘要或答案；代码不替模型挑选要点。原文是否相关、回答是否忠实仍由模型及外部验收判断。

`submitted` 只表示提交；`acceptance=not_evaluated` 明确表示尚未验收。调用预算在生成入口检查，时间预算中断当前任务，不伪造完成。精确 token 与 State 关系在原始 trace 中保留；日志缺失或请求失败必须作为证据缺口处理。

`--concurrency 2` 调度完整独立任务，每个工作进程使用独立 State、存储和输出目录。不把简单问题切碎，不自动集成相互依赖的任务，不支持并行修改合并。共享服务容量与实际质量决定并发上限；任务合格率、端到端时间与包含失败的总消耗一起衡量，不能仅凭并发数推断收益。

外部审核使用 [任务结果审核规范](TASK_OUTCOME_REVIEW.zh-CN.md)：看问题是否被回答、缺陷是否有证据与可复核方法，不限定工具路径；允许“未发现该问题”，不将建议的测试视为已经运行。

参考 `rwkvrag` 的原文来源保留和独立任务并发，不移植固定 Reader/Writer 流水线。长文材料选择和层次汇总需要后续单独验证，当前入口未证明长文问答或全仓库审查稳定。

当前默认 `tool_scope="files"` 只公开生产 `read_file`（以及模型提交答案的 `final_answer`），适合已知文件位置的问题；模型仍自己决定读取参数和何时回答。需要自主搜索定位时显式设置 `tool_scope="inspect"`，公开既有只读搜索、目录、摘要及检查工具。该范围尚未达到固定组稳定门槛。

可选复核不是每步关卡。先用 `scripts/request_rwkv_read_only_advice.py --parent /absolute/path/previous-output --file README.md --output /absolute/path/advice-receipt` 获取一份显式建议。随后创建同工作区、同问题的新任务，填写 `reconsider_from` 为旧输出目录、`advice` 为收据中的建议原文、`advice_model` 为收据模型身份。复核继续原 State；新输出目录保留完整 `PARENT_TRACE.jsonl`、父结果、父快照、`CONTINUATION.json` 与新调用。原结果不覆盖；新答案仍由 RWKV 生成。建议者只看问题、指定原文和候选答案，不掌握完整工具执行记录，也不代表验收器。

2026-09-13 固定文件组：8/8 读取并提交，任务合格3/8、部分满足1/8、不合格4/8。六次强模型建议和建议来源标签对照均未提高这个任务合格数；部分缺陷描述改善，但错误数字、虚称运行验证仍存在。入口可用于有外部复核的文档问答与代码检查，尚不能作为无需复核的可靠审查者。固定组连续两遍全通过门槛未达，不升级写任务或长文流水线。
