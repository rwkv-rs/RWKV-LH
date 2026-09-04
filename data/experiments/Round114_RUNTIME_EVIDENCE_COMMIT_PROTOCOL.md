# Round114 Runtime / Evidence / Commit Protocol

## 目的

修复 Round113 定向 14 题暴露的通用运行时与证据接口缺陷，同时保持业务语义、操作、参数、文件内容、Task/Goal 完成决定和最终回答均由 RWKV 产生。

## 冻结变更

1. Python 命令沙箱显式挂载项目虚拟环境 site-packages；`python -m pytest` 与虚拟环境 console script 必须可用，仍不挂载项目仓库或验收资源。
2. `check_command` / `run_command` 增加 RWKV 显式提供的 `expected_exit_code`，默认 0；harness 只比较模型调用中预先给出的值，不从 Goal、输出或 verifier 反推。
3. `file_content_read` 接受成功、主体匹配且有可见输出的只读命令观察；这只建立结构观察类别，不判断输出是否满足 `done_when`。
4. 有本 Task workspace mutation 时，路径型 evidence subject 必须对应至少一个本 Task mutation target，防止输入文件证据替代输出观察。
5. Task action/result 与 Goal projection 中的 deterministic checks 明确改为 operation-effect checks，并声明它们不验证自然语言 Task/Goal 语义。
6. `completion_protocol_ready=true` 时生成紧凑完成检查点：展示最新实际观察、精确 `lh_task_done` 线格式和“成立才提交，否则选择不同操作”；不自动提交。
7. Goal planning 明确 `after` 是 AND，不表达条件；fallback/按 outcome 继续的普通流程优先放在同一个端到端 Task。
8. 格式转换层只增加一种已观测的常见嵌套 Task envelope。只有 task id、operation 和参数全部由模型明确给出且重复字段无冲突时才展平；冲突继续拒绝。
9. 每个 terminal status 都必须产生非空用户回答；有效 RWKV Final 原样交付，模型不可用时的运行时兜底明确说明不是完成证据。

## 固定验证集与参数

- 离线：完整 pytest，显式使用项目 `temp/` 作为 `TMPDIR`。
- LH-Control：固定 30 题、固定参数与现有相似度口径。
- 在线定向：与 Round113 完全相同的 14 题，`--max-transitions 200 --concurrency 1`。
- 通过定向门槛后再运行完整 E2E-90，不在观察结果后更改评分口径。

## 预登记指标

- 离线回归全部通过。
- LH-Control 全部通过。
- 定向 14 题 `final_output_nonempty=14/14`。
- 定向 Strict E2E 不低于 Round113 的 `4/14`，目标 `>=5/14`。
- 外部正确不低于 `7/14`。
- FP 不高于 Round113 的 `5/14`；B11 的错误 evidence subject 不得再直接完成。
- B14 的正确 `cat` 内容观察不得被工具名边界拒绝。
- B27 只有在 RWKV 显式给出预期退出码或在可见失败后重新给出该显式调用时才能完成；控制器不得从自然语言提取退出码。
- Python 沙箱诊断中 `python -m pytest --version` 和 `pytest --version` 都成功。

## 禁止项

- 不读取或回流隐藏 acceptance/verifier 结果。
- 不由控制器选择工具、生成参数、计算业务值或修改 artifact。
- 不根据用例 ID、文件名或标准答案特判。
- 不把格式归一化扩展为字段猜测、冲突消解或语义修复。
- 不把 effect check、hash 或文件存在误称为 Goal 语义通过。

