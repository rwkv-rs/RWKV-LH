# RWKV-LH 单一产品链路清理第一阶段结果

日期：2026-09-04（Asia/Shanghai）

## 判定

第一阶段通过；整体项目清理尚未完成。

- 冻结起点：`3f23a6a6`，已同时保存到远端分支 `chase/rwkv-goal-loop-v2-cleanup` 和固定备份分支 `chase/pre-cleanup-20260904`。
- 当前工作树相对冻结点：54 个已跟踪文件发生变化，新增 22 行、删除 9725 行，净减少 9703 行；其中删除文件 38 个。
- 本轮没有训练、生成、加载或选择任何 StateTune。
- 用户已确认工作树中既有实验记录的删除是有意操作；未跟踪的大型历史数据与实验产物未被本阶段修改、提交或上传。

## 已删除的旁路

1. 退役 0.4B State Router/Shadow 的服务、HTTP 客户端、协议、模型、训练、评估、WKV 投影、Web API、CLI 和测试。
2. 重复的旧 `rwkv_lh/web_assets`，正式产品 UI 只保留 `rwkv_lh/goal_web_assets`。
3. Hybrid Supervisor、Contract Graph、ECRA、State Router 与旧论文快照等历史设计文档。
4. 已退役的 `rwkv-lh-control` 与 State Router 控制台入口。

为当前 25 类 Selector 服务保留 `rwkv_lh/state_router/local_backend.py` 兼容加载后端；它只负责本地 vllm-rwkv 模型/tokenizer/隐藏状态提取，不再提供 State Router 决策。

## Selector 全链路诊断

工具不存在不是阻断原因。

- 固定协议包含 25 个标签：23 个实际操作、`final_answer` 和 `ABSTAIN`。
- 13.3B native RWKV 模型服务可用，状态创建、追加、分叉、生成、提交、回滚、导入、导出和恢复能力均由健康检查确认。
- manifest-free zero State 的 profile manifest 身份已固定为 64 个零字符，修复了示例与本地运行配置中该字段为空的问题。
- 当前 Selector 唯一明确的启动阻断为：`RWKV_LH_SELECTOR_HEAD_SHA256` 和 `RWKV_LH_SELECTOR_HEAD_HASH` 缺失。
- 这两个字段标识并校验“隐藏状态到 25 个标签 logits”的分类 Head 产物；它们不是工具名、工具实现或 StateTune。
- 旧 Head 不可直接冒充新产物：旧特征抽取使用独立 bootstrap 行，却声明为持久因果轨迹。当前代码保持 fail-closed，不允许 13.3B 或启发式逻辑绕过 Selector 替代选择。
- 配置错误现已直接列出缺失字段，避免原来的笼统身份错误。

因此，在没有生成并冻结一份符合当前真实状态轨迹协议的 25 类 Head 前，不能把“总选两个工具”归因为 2.9B 基座模型能力，也不能通过 StateTune 先掩盖该问题。下一项有效实验应先重建合法 Head，然后在固定全数据集上分别测选择分布、类别召回和完整任务成功率。

## Executor-Args 独立冒烟

记录目录：`../RWKV_LH_ZERO_STATE_EXECUTOR_PROTOCOL_V1_20260904/`。

- 有效 R3 使用 13.3B native zero-State，固定四种已选 operation：`list_directory`、`read_file`、`write_file`、`run_command`。
- 首次生成 `4/4` 通过；模型输出的 `name/arguments` 均被 parser 转换为规范 `function/params`。
- 四次均保持上游 operation，Harness 只补注册表默认参数，没有生成语义参数；未实际执行工具。
- 这证明当前模型在干净的逐 action 状态下能够填写这四类参数，旧 trace 的 12 次连续 action 协议失败不能解释为“13.3B 完全不会格式”。它仍只是四例协议冒烟，不等于完整 Executor 能力评测。

## 固定验证结果

- 当前链路定向测试：`182 passed`。
- 清理后的完整测试：`785 passed, 1 warning`，两次完整运行一致；警告为 Python 3.13 下既有的 `multiprocessing.fork` 警告。
- Selector 配置与服务定向测试：`27 passed`。
- `compileall`：通过。
- `git diff --check`：通过。
- `uv lock --check`：通过。
- wheel 构建：通过。
- wheel 内容：旧 `web_assets` 0 个，正式 `goal_web_assets` 3 个，`state_router` 仅剩 2 个兼容加载文件，控制台入口仅剩 5 个当前入口。

## 尚未解决的工程问题

本阶段没有把以下债务误记为已解决：

1. wheel 仍打包 125 个 `scripts` Python 文件，大量属于历史实验驱动，不应长期进入产品发行包。
2. `rwkv_lh/controller.py` 约 5929 行；当前 StatefulGoalLoop 静态方法闭包只触达基类 103 个方法中的 21 个，另外 82 个主要属于 Contract Graph、parallel atoms、online 等历史链路，需要单独预注册后剥离。
3. `rwkv_lh/exact_tool_selector` 同时保留 compact protocol v3-v8 和多代模型/训练实现，协议代际还未收敛到一个可发布路径。
4. 合法的当前 25 类 Selector Head 尚不存在，所以完整 Agent Ladder 不能启动；这是当前首要运行阻断。

这些项目需要继续分阶段清理和全量回归，不能仅凭本阶段 785 个测试通过宣告整个工程完成。
