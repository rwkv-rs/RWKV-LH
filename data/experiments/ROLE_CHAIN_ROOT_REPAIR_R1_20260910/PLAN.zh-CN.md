# ROLE_CHAIN_ROOT_REPAIR_R1_20260910

起点：本地 d0f2d180；依据 ERROR_PROPAGATION_AUDIT_R1_20260909 的 EP01–EP08。
Owner 已授权修复；当前五角色及逐角色训练顺序保持。

本轮先做工程修复。Agent 基线沿用原 R3：Strict 0/3、completed 0/3、mutation 0、动作 2；终止分别为阶段服务不可用、Planner 服务不可用、连续协议拒绝。该基线不重放、不重评分。

## 冻结的修复验收条件

1. Executor 与 Step Auditor 的唯一输入 builder 明确收到不可变原始需求和当前步骤；生产与 trace 重建逐字节相同。创建内容可以由需求推导，复制已有事实仍受精确来源约束。
2. 工具每个路径参数的结构前置条件和读写副作用来自同一声明。空工作区不能因 destination 可创建而放行无 source 的 copy/move；copy 可读取写范围外的合法源，move 不得删除写范围外的源。有限发现保留 unknown。
3. 两次同工具参数拒绝后的重新选择收到该步骤、该 revision 的持久失败事实；保留原语义反馈，重启不丢失，不转 Planner、不重复已执行动作。
4. discovery_complete=false 在生产输入、trace 重建与数据校验中一致，不补成 true。
5. Native 生成明确请求真实输入 token 证据，只有服务器完整上下文 token 与本地逐段重建匹配才算合格；不得伪造 BOS 或 full_context。
6. Selector、Step/Final Auditor、Finalizer 不因 Executor 物理缓存不可用而无法开始。工具交接仍持久绑定需求、事实、工具定义、模型/State 身份；恢复不能重新采样已提交的选择或重复动作。
7. 每个修复先失败后通过；完整 tests/ 全绿、0 skipped，包含 Torch/State 和浏览器。旧协议入口及字节码清理，当前协议版本唯一。

工程测试不作为角色训练数据，optimizer steps 0。每个实测单独冻结源码、模型、服务 manifest 和运行预算；现有原始运行与切分、门槛不修改。本轮不读取 Holdout、私有验收或参考实现。验证、SHA 清单和剩余限制在本目录记录，完成后立即本地提交。

扩大目录检查发现整改中的完整参数展开会放大输入：300 文件夹具的 Executor 22783 tokens、Selector progress 18126 tokens，均超 16K。新增先失败的回归后，将完整机械合同留在日志，Selector 仅取参数可用性摘要、Executor 仅取已选工具的合同与发现提示。提示投影预算每参数 32，所有显式 roots 原样保留，省略发现内容必须标记 incomplete。工程夹具要求各角色投影低于 8192 tokens，为原始需求和证据保留空间；该阈值只用于此夹具，不修改生产任务输出预算或角色数据门槛。

2026-09-10 owner 再次明确：不是补丁堆叠，而是整体替换错误交接架构；完成整改、测试后，根据缺陷推进 StateTune。服务器当前 Native 服务和 worker 的源码与本地 Git 2dd1166a 内容 SHA 完全相同。本轮将这部分已有运行实现纳入当前源码和回归，移除部署引擎中的重复模块；不会混入其他工作树未提交的 R35 改动或恢复旧 Controller。
