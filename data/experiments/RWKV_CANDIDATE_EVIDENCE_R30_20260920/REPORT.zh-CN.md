# R30：候选State证据封存与回收

本轮不新增Agent任务成绩，不训练、不调用教师。R29训练继续在其独立冻结源码上运行，未修改正在运行的训练代码或647条数据。

## 问题与修复

候选评测准备时发现：`seal_run → export_boundaries → replay_run`共用的回放器写死zero profile。该约束适用于本轮zero来源训练数据，却会拒绝合法的非零候选评测证据，阻断后续安全回收State。

修复为证据调用方显式传入事前登记的State profile id与SHA。回放器同时核验所有checkpoint声明与Native cache binding，错误profile在发布证据前拒绝；不从trace自动推导一个允许任意State的授权。封存manifest与边界记录明确保存该profile，仍然标记training_admitted=false。训练准入调用不传该参数，继续只接受zero来源；没有把候选成果伪装成zero样本。

这次只变更证据回放/封存接口，没有改变RWKV输入构造、工具选择、参数、原始输出、任务预算或评分。

## 验证

- 历史R6真实候选trace：先2失败/1通过，修复后候选可封存、错误SHA被拒绝、训练默认仍拒绝非零来源。
- 相关46回归通过。
- 当前全部535个来源、647条训练边界重新回放，输入文本、精确token、request与checkpoint保持一致，zero profile校验通过。
- 完整1910回归通过、0跳过，日志见FULL_TESTS.txt。原作者脚本的一条转义SyntaxWarning保留，未改被冻结的历史脚本。

评测执行源码已重新冻结在evaluation/source，变更相对R29训练源码仅上述三个证据模块。R29原训练与评测登记保持原件，evaluation/EXECUTION_SOURCE_ADDENDUM.json事前记录执行源码变化；72次评测将统一使用新源码，保留原12个未入训开发任务、评分、采样、预算和两遍重复，不拼接R27成绩。候选任务输出尚未读取。
