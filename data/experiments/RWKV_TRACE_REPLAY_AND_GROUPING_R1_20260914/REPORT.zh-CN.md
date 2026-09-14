# RWKV_TRACE_REPLAY_AND_GROUPING_R1_20260914

## 任务级结果

本轮没有新增模型执行或重评旧实验；项目 Strict 不适用。复用明确操作实验两次失败：任务合格0/2、提交回答1、实际修改0；一次重复保护中断，一次提交错误修改声明。原结果与评分不变。本轮是离线来源工程修复，不是模型能力提升。

## 来源重放结果

同一生产 replay_run 对两条编码轨迹重建7+4=11次生成，全输入token、原始输出及native State父链校验通过，request_id见REPLAY_RESULTS.json。错误回答仍原样保留，不生成纠正文本或训练标签。来源归档SHA、模型SHA、重放器与分析脚本身份在REGISTRATION.json；抽取只读归档成员，不执行历史工具。

## 已确认工程问题和修复

RESULT记录tool_scope=coding，但重放器把所有非空scope送入ReadOnlyHarness；后者明确只支持files/inspect，编码轨迹必定被拒绝。改为coding使用生产ActionHarness，未知scope仍拒绝。重建目标取state中记录的workspace身份，而不是推测execution/workspace；后者是身份一致性修正，本轮未单独证明它导致bootstrap差异。共享bootstrap与event构造器未改，未增加模型调用、参数补偿或答案改写。

影响范围为现有direct来源重放/准入，不改变在线Agent执行。已有只读与旧观察拒绝回归仍通过。编码可重放不等于编码纠正可训练：现有标签准入仍限已实现的读取/摘要类型，编辑纠正验证是后续工作。

## 红绿与边界

RED.log：10通过、2失败。真实coding重放测试复现unknown read-only tool scope；另一项篡改目标拒绝测试原先预期bootstrap错误，但生产更早以literal request digest mismatch拒绝，修正测试预期，不修改生产拒绝机制。GREEN.log记录12通过。完整测试1652 passed、0 skipped，耗时312.51秒，见FULL_TESTS.log。

本轮没有遍历全部历史编码run，11次重放不是完整来源覆盖声明。旧renderer拒绝仍保留；未接管强模型成果、未创建dataset、未训练、未push。Owner五处diff与前轮完全一致，见OWNER_PRESERVED.json。

## 项目参考和缺陷整理

附件PDF身份见ARTICLE_SOURCE.json，官方资料与适用边界、19项问题/正向控制的分组见docs/DEFECT_GROUPING_AND_NEXT_STAGE.zh-CN.md及docs/DEFECT_REGISTER.zh-CN.md。NeoHorse启发的是证据反馈与数据审核；不据Qwen后训练结果预言RWKV StateTune收益。

下一增量：实现来源可见的编码纠正候选验证，隔离执行并核对差异和实际入口行为；再审核子类覆盖和来源家族切分。1万条仅计划，不能用机械改写凑来源量。
