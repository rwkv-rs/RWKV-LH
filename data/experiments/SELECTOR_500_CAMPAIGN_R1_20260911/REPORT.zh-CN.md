# Selector500 采集已启动

记录时首题 E2E-B01：Strict 0/1、completed 0/1、动作 3，文件内容通过外部检查但没有 RWKV Final，不能称为 Agent 完成。首批其余任务仍运行，不能提前填本批最终分数。之前轮次 A 为 Strict 0/4、completed 0/4、mutation 0；optimizer steps=0。

Owner 已要求至少500条，解释为至少500条经过复核、固定去重后保留的 train 样本，原3dev/2confirmation另保留。独立选择边界至少167个，并单独报告 train/全体边界；三种不同菜单顺序是现有生产训练格式的三个样本，不冒充三个独立场景。500只是数量门，不保证 Selector 已合格。

任务池预注册98个公开开发题，固定按五个 suite 轮换及各自 task ID 排序，12题一批；原任务和验收不改写。生成前排除1个 Selector 不支持的 mock_api 题及2个在线网络题，公开题目按原0.95相似度排除重复。全部是已编写的开发基准，由实际生产 Agent 运行获得 trace，不是直接合成角色训练行，不冒称真实用户请求。不读取最终保留集。每题1800秒/200 transitions、单任务并发、整批21600秒，不重跑择优；先保持全零 State、Executor1800及原模型配置。

原已完成提交 push 至3ae1efcc。隔离工作树 /home/chase/GitHub/RWKV-LH-selector-500-r1-20260911 精确冻结该提交；rwkv_lh/scripts/tests/依赖与1479 passed的5edcccde一致。主工作区另一个工程过程的 harness/supervisor/测试修改不进入本轮。服务器从本地上传，132项项目清单和6393项engine清单逐文件核验并启动，服务健康及模型身份已通过；服务器无Git。新项目manifest SHA524a195270d8d10062e87a17a7c0c5dba36ceae3c83e3413ca34c85a01def0c5，engine SHA9fdfd8e8b11f6c6de3df30ae9e36088765cf9780831595b49150d4e95375b32a。

当前24条数据只用于 Selector2.9B 的工具选择：19train、3dev、2confirmation。来自22个生产来源的256条候选，依次核验来源SHA、原始事件和完整服务器token、用唯一生产builder逐字节重建、绑定执行证据/Planner合同或双AI语义复核标签，再按预注册边界聚类和固定回归anchor去重。最终包含write_file9、list_directory9、check_command3、search_text2、read_file1。当前标签权威为执行证据14、Planner合同3、双AI复核7；字段名human_double_review是现有schema名称，实际reviewer明确标为AI。waiver只批准特定旧源码与当前源码的准入，不证明标签正确，也不增加样本。

每行训练输入是该真实边界下的目标、步骤/进展、可见证据和候选工具菜单及其完整token；目标是生产协议格式的正确工具名，例如 SelectorIntentV6: check_command。失败的Agent任务仍可能提供合格选择样本，但无依据、错误或分歧标签不直接进入训练。参考实现、隐藏验收及未来结果不进入模型输入。

本次首题管线探针无waiver抽出3条自动候选、6条待复核；探针不是最终去重数量，且不与整批重复计数。有效训练总数目前仍19，未声称500达成。整批完成后再核验所有边界、双AI复核、与既有来源按原政策统一去重、密封并重放。任务池耗尽仍不足500时先登记新独立任务池，不降低门槛或复制行。

满500且覆盖/完整性/相似度门通过后，才发布密封freeze，登记真实optimizer smoke和Selector StateTune。训练冻结底模权重，只学习Selector初始State；固定dev/confirmation与zero比较通过后，固定合格Selector State进入Executor采集。不会仅凭达到样本数就切换角色。

运行状态：../SELECTOR_500_BATCH01_20260911/PROGRESS.json；开始凭据STARTED.json；每题原始日志、audit及trace完整保留。此文是启动记录，不是整个500条采集完成报告。
