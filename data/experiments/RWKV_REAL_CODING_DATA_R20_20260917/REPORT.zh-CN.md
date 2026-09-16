# R20：真实仓库诊断纠正增量

## 任务级与数据结果

原三项项目任务没有完成，本轮没有修好整个 Loguru/AnyIO 项目；这不是项目 Strict。产出3条真实 RWKV 生成边界上的合格诊断动作，来自3任务、2仓库家族。修改样本0、交付完成样本0、训练0。正式数据为 frozen_increment/train.jsonl，唯一生产输入重放、原始模型/State谱系与精确输入token保持不变。

- Loguru：从无关文档阅读转为实际触发栈帧不足，观察到 ValueError: call stack is not deep enough。人工大depth是栈帧不足探针，不冒称真实Cython或atexit全覆盖。
- AnyIO stdin：从浏览依赖转为AST检查真实run_process签名，观察到缺少stdin参数。只是接口诊断，不代表子进程行为已修复。
- AnyIO tempfile：从把文件当目录重复调用转为检查四个公开API，确认当前都缺失。只是公开入口诊断，不代表异步实现正确。

## 准入证据

Codex根据当时用户目标和可见工作区材料写候选；Qwen3.8两次隔离会话独立审核，原请求/响应保留。两次审核使用同一模型，不声称跨模型独立。前三条v1及拒绝意见保留：审核将expected_exit_code=0的预期失败测试视为矛盾；这并不说明先失败测试无效。v2使用check_command、显式预期退出1，准确表达诊断目的，同时选择较早真实边界减少重复上下文，未截断/改写输入。

每条经现有validate_command_correction隔离执行，再经revalidate_training_command重新执行，最后freeze_direct_dataset再复验。命令实际退出1和具体错误文本均核对，未把任意失败当复现。验证在WSL UbuntuRecovered的真实ActionHarness沙箱执行；Qwen审核在服务器18244本地执行，无API转发。私有答案和未来观察未放入教师输入。

三条输入分别6890、10304、10052 token，目标96、209、137 token，总442监督token。生产collate_samples验证prompt/padding标签全部-100，仅目标参与loss；16K完整容纳，无截断。旧300条训练数据无相同(request_id,target_text)重复。

正式冻结沿用旧版不变4 dev/4 confirmation角色回归及相似度阈值，代码自动完成隔离检查，不向教师或训练模型提供评测材料；未访问Real Agent Holdout。dev/confirmation均复用，不是新增8条。AnyIO两任务同一仓库家族，不跨训练与评测切分。新包保留在experiments，不新增data/datasets版本。

## 使用与限制

使用 frozen_increment/manifest.json 及 train.jsonl；READY_ROWS.jsonl是冻结前候选，合并时以正式包为准。该增量用于补“定位失焦、实际复现、执行推进”，不是一次完整code agent训练方案。下一批应从可见源码边界加入修改与真实反馈修复；不把教师整段接管结果当同输入标签，不靠这3条宣称能力提升。

## 同期教师状态

R19首次脚本误将seed写入受保护request_options，预检失败且零模型调用，移除此覆盖后按生产默认重新冻结运行。2048思考上限已实际生效，但两题均重复调用中断、产物0/2；4096对照仍需以最终记录为准。1024队列暂停，19已记录均未通过（14输出预算耗尽、4重复调用中断、1提交但未通过）；另2在途因暂停中断，原件保留待显式核对，不自动重试。不启动训练、不push。

完整回归：1894 passed、0 skipped，343.89秒。正式增量SHA见FREEZE_RESULT.json和EVIDENCE_SHA256.json。
