# 架构整理与独立任务交付阶段 R1

## 任务级结果

真实并发混合批次 **2/2满足事前任务要求、2 submitted、mutation0、虚称执行0**。健康检查脚本总结准确；递归扫描测试经RWKV自主选择命令实际执行，exit0且JSON checks/passed为true，原回答与结果一致。独立State及原输入/观察父链核验通过。

这是两项获准旧用例的一次集成smoke，非项目Strict、固定双遍稳定门、性能A/B或通用修复能力验收。第二项使用coding副本权限，任务仍要求不改文件；它证明可写分发入口中的测试交付，不证明本轮RWKV修改成功。四次生成、11936逻辑输入/396输出；零新strong、训练或dataset版本。未测成本/吞吐收益，全量工程测试同时在本地运行，不使用本轮计时作性能比较。

## 架构整理

新增ARCHITECTURE.zh-CN.md作为当前产品唯一导航，明确RWKV、Harness、调度、strong与外部验收职责。README、第一版设计、旧角色规范和CLI帮助指向当前入口；旧product_runtime多角色构造明确为历史研究/检查接口，不再自称当前产品入口。

HANDOFF从602行历史叠加整理为当前状态、能力限制、后续顺序及证据索引；旧分数和证据仍在原报告及Git历史，不新建retired/archive目录，也不把旧失败重算收益。保留HANDOFF修改前SHA。历史角色源码和研究测试尚未物理删除，依赖及owner未提交修改仍在，不能宣称代码全部清理。当前产品直接执行，不自动启用旧角色链。

## 下一阶段已落地的实现

新增agent_batch.run_agent_jobs统一读取/检查/修改任务调度，复用已有_run_job和coding复制/真实快照；删除read_only_agent重复调度实现，由旧只读入口委托同一函数。新增scripts/run_rwkv_agent.py作为混合独立任务入口。它不是新的模型协议或第二套Controller，不拆任务、补参数、改答案或拼接State。

全批启动前检查ID、scope、调用/墙钟预算、源目录及输出交叉重叠；并发用spawn进程，每个任务独立State。普通worker启动异常作为error结果返回，其他任务继续，原模型结果原样返回；进程池整体故障仍抛批次异常并保留已落盘证据。所有修改只在副本交付，源目录不变，不自动合并、不暗示依赖任务已集成。

本阶段实现独立任务批量交付这一里程碑；strong建议/接管产品路由、依赖任务集成与自动合并仍未完成。既有显式strong实验接口保留，下一步在统一入口上产品化，不能把实验能力冒充已完成自动协作。前端/可视化未改。

## 回归与审计

新增测试先因模块缺失失败，覆盖混合任务异常隔离、非法并发数、源/输出交叉重叠及全批预算预检查；实现后相关34 passed。全量 **1637 passed，零跳过，311.74秒**，包含Torch/State/必需浏览器检查。RED/GREEN/FULL_TESTS保留，未并行启动多个pytest。

真实任务使用预先冻结的LIVE_REGISTRATION/JOBS、获准seed_files原文、相同模型与采样、独立zero/native_required；外部评分要点不进入模型。并发2进程由实际CLI启动，所有4代逐token从生产renderer和checkpoint重建。model/native父SHA匹配，读取字节、真实命令流与exit码核验；工作区隔离及原始源文件SHA保持。验收见LIVE_REVIEW，按事前自然语言smoke标准，不伪称已冻结新的正式回归集。

所有修改不涉及owner五处原diff，按字节比较保留，未混入本轮提交。全量源码/测试身份见RELEASE_SOURCE，真实证据归档及逐文件SHA见raw_evidence.tar.gz/RAW_FILES_SHA256。无新训练/数据版本，未push。

## 使用

`.venv/bin/python scripts/run_rwkv_agent.py --jobs /absolute/jobs.json --concurrency 2`

格式见docs/AGENT_BATCH.zh-CN.md。本轮JOBS中的输出已存在，不能原样重跑覆盖；复制清单并换全新的output_dir。stdout是批次原结果，可重定向保存；每项目录保留trace/State，coding交付含DELIVERY及修改副本。退出0只是所有任务提交，不等于外部合格。
