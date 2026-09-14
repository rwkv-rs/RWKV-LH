# 社区StateTune实现核对与下一阶段准备

日期2026-09-14。只读查看外部文档/源码，无训练、推理服务切换、安装依赖、前端修改或数据版本发布。Agent/角色级无新运行指标。GPU约束仍仅0号。

## 来源身份

- Alic-Li/rwkv_lightning_cuda main查询：81584b010f09fad94d01f81473c486d574cf9c6b。查看README、docs/run.zh-CN.md、src/state_tuning/README.md、HTTP API及HIP说明。文档来自在线main视图，head是查询时身份，后续实验须重新冻结完整源码。
- No-22-Github/Preen main查询：5ff2a3c68505952ceb6bf2e01c5c60293de78102。查看README、src/statetuner/data.py、export.py；同上，尚未构建/运行。
- RWKV-APP/statetuning浅克隆到temp/statetuning_reference_20260914，仅供阅读；本地HEAD 23b2f3f49c88d3b1f7ecb59feb89fda6147d93cd。GitHub缓存首页不完整，以此提交实际README及PySide/Flutter捆绑源码核对。

## 对项目有用的部分

1. [Lightning独立训练实现](https://github.com/Alic-Li/rwkv_lightning_cuda/blob/main/src/state_tuning/README.md)：免Torch的CUDA/HIP状态训练、分块重计算及State梯度跨块传递、训练/推理共用权重加载和State文件解析。可作为后端候选，不替换我们的任务协议、Harness或验收。其batch-size当前是逐样本梯度累积，不能据此宣称GPU样本并行收益。当前text JSONL做因果下一token loss，按ctx截断；不直接等价于本仓库精确token、目标段监督、不截断训练。梯度文档明确全模型Torch对齐仍是单独验证任务。
2. [Preen数据实现](https://github.com/No-22-Github/Preen/blob/main/src/statetuner/data.py)：训练/推理模板同源、prefix/target边界及目标段mask、终止符训练；[导出实现](https://github.com/No-22-Github/Preen/blob/main/src/statetuner/export.py)包含State回读和挂载比较。我们的statetune_core已有目标段mask及精确time_state可训练集合，应该对齐验证，不重复另写一套。它基于Apple Silicon/MLX，打包Python运行时，不是当前WSL/NVIDIA训练后端的直接替代。其默认超长截断与随机行切分不适合直接用于本项目来源家族隔离的数据策略。
3. [State-Tuning Studio](https://github.com/RWKV-APP/statetuning/blob/23b2f3f49c88d3b1f7ecb59feb89fda6147d93cd/README.md)：模型/数据/训练参数、loss记录、导出及本地试用流程可借鉴；Flutter与PySide两个客户端，底层仍PyTorch。当前不开发UI，后续可让UI消费统一训练run/manifest。核对到lib、assets、pyside_desktop存在不同捆绑脚本，不能混用：lib旧dataset有tokenizer失败后的随机token后备，assets/PySide改为报错。PySide仍按text全序列labels训练、截断/零padding，无我们的目标段mask；不直接导入为正式Agent训练器。

## 必须具体对齐的接口

- State的key/shape相同不代表轴语义一致。Lightning文档规定运行时[H,K,V]、PTH[H,V,K]转换；Preen x070导出沿其训练方向不转置。不能仅凭文件扩展名判兼容，也不能未经对齐就判任一实现方向错误。用非对称State验证导出回读及相同输入下logits/续接。
- Lightning的HTTP API文档包含Python与C++两部分，不能混淆两者stop参数。C++使用token ID stop，文档还指出流式结束原因/usage信息不足。接本项目时必须真实区分EOS、预算、中断，并获得可重建输入/输出token和父子State证据，不能把统一stop当自然完成。
- GUI可用、二进制能启动、loss下降都不是本项目任务验收通过。对照必须保持模型/tokenizer、生产输入、监督mask、采样与预算，并分别报告数值/任务/资源结果。

## 下一阶段顺序

A. 主线：盘点现有获准生产trace的可重建边界、独立来源家族、长度和缺陷覆盖；借上一轮纠正验证保留有效候选与失败证据。明确修复目标、事实忠实性、有效修改/入口接入、真实测试反馈及成功保持共同覆盖，继续统一多缺陷State，不按每个小阶段训练一个State。

B. 有界后端准备：冻结Lightning源码/二进制、模型与tokenizer；只用GPU0验证加载、State非对称导出回读、同token输入前向/续接和隔离。当前未执行。若训练数据入口不能保持精确输入/目标mask，登记最小适配范围；这项适配不阻塞使用已经验证过的现有训练器。

C. 训练前登记：获准数据版本、来源家族隔离、固定zero回归、模型/State身份、优化步数与资源预算、成功保持阈值。可先做不更新参数的前向/loss/梯度一致性验证，正式optimizer训练按授权登记。不能要求zero先完成待改进任务，也不等所有工程增强完成。

D. 统一训练后，用固定任务比较zero/tuned，读取与事实、有效修改、测试反馈、合格交付及全部失败重试成本分别报告。只有数值/任务证据支持才保留新State或切换后端；训练与运行后端更换不混为一次收益。

当前交付是研究与准备清单，未宣称三者已在本机兼容或跑通。生产代码/测试未修改；沿用上一轮GPU0完整1700 passed、0 skipped（327.49s），日志RWKV_CORRECTION_USAGE_R1_20260914/FULL_TESTS.log，本轮不把它算作外部项目测试。Owner五处修改保持。
