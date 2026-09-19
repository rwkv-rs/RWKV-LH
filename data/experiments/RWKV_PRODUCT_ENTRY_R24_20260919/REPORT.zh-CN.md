# R24：恢复实际可用的编程任务命令

新增Agent任务运行0，completed0、mutation0，Strict不适用；本轮是产品入口工程修复，不是模型能力提升或完整成品验收。训练0、模型API0、子代理0、未push。

## 缺陷与修复

`pyproject.toml` 的 `rwkv-lh` console entry仍指向已删除的 `scripts.run_long_horizon`，实际安装命令连 `--help` 都以ModuleNotFoundError失败。README同时保留旧start/status/resume与五角色运行说明，用户无法按入口完成任务。这是打包及文档缺陷，不是RWKV问题。

入口改为已有 `scripts.run_rwkv_coding_agent:main`；执行循环、工具选择、参数、观察传递和State逻辑不变。README给出当前单任务命令、工作区副本、产物目录和退出码含义，并移除过期命令/角色说明。没有增加强模型调用或前端开发。

## 验证

同一回归先失败2项、其余4项通过，修改后6项全部通过；遍历所有5个声明入口的import与help，另外核对默认入口接收编程任务参数。uv frozen同步后安装命令help实际通过。完整工程回归1900 passed、0 skipped，349.25秒，包含既有Torch/State/浏览器检查。Owner五处修改逐文件SHA保持不变。证据见REGRESSION_RED.txt、REGRESSION_GREEN.txt、INSTALLED_ENTRY_RED.txt、INSTALLED_ENTRY_GREEN.txt、FULL_TESTS.txt、RESULT.json。

## 成品交付范围与剩余工作

首版按CLI编程Agent交付：用户提供工作区和一句目标，RWKV自主读取、修改、调用测试和反馈。外部验收检查实际文件和行为，提交回答不算通过；保存原始回答和失败记录。前端暂不开发。

工程入口已恢复，但当前不能声称普遍自主编程稳定。仍需完成1000条高质量数据目标、冻结训练数据/源码/预算，运行一轮统一StateTune，再在与训练隔离的固定任务上比较zero与候选。只有质量门通过才推荐候选State；失败则保留基线、报告具体缺陷，不宣称训练收益。

报告应提供可以实际重跑的任务命令、实际生成文件、真实测试输出、State身份和限制；不以预写答案或脚本代替RWKV。复用现有开发回归做趋势比较，另行预注册未入训任务验证泛化；最终Holdout不用于调试。

完整命令见仓库README。资源成本和吞吐须在相同验收质量下实测；本轮没有测得新收益。
