# 13.3B zero-State Executor-Args 协议冒烟预注册

日期：2026-09-04（Asia/Shanghai）

## 目的

在 Selector Head 缺失、完整产品 Ladder 无法诚实启动时，单独检查 13.3B Executor-Args 是否能在“工具已由上游固定”的真实当前协议下填写参数。该测试不评价工具选择，不执行工具，也不替代端到端结果。

## 冻结配置

- 模型：当前 `RWKV_LH_EXECUTOR_*` 配置指向的 G1J 13.3B 服务；运行记录保存模型名与 profile 身份。
- State：显式 zero identity；每个样本重新 bootstrap，不继承上一个 action 的 WKV。
- 协议：`rwkv-lh.g1j-per-stage-state-tuning.executor-args.v1`。
- sampling：生产 `LongHorizonModel._SAMPLING`，temperature `0.1`、top_p `1.0`、top_k `0`、penalty_decay `0.996`。
- 每样本最大输出：768 tokens；每个样本只调用一次，不做 parser repair 或重试。
- 不训练、不加载或选择任何 StateTune。

## 固定样本

1. `list_directory`：列出 workspace 根目录；
2. `read_file`：读取 `input.txt`；
3. `write_file`：把 `alpha\n` 写入 `result.txt`；
4. `run_command`：在 workspace 中执行固定 Python 输出命令。

上游 operation 在测试数据中确定性指定，只用于隔离 Executor 参数能力；不得把结果解释为 Selector 正确率。

## 判定

- 主指标：首次生成同时通过当前 transport stop 恢复、canonical command parser、Executor-Args parser、选中工具保持和 Harness 参数规范化；门槛 `4/4`。
- 辅助指标：原始输出、finish reason、token 数、normalization trace 和错误逐样本保存。
- 任一样本失败即按原结果记录，不修改 prompt、采样或评价口径。
