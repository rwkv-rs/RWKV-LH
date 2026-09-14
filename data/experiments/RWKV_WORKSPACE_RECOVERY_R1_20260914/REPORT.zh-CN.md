# 工作区与恢复边界整改

轮次：RWKV_WORKSPACE_RECOVERY_R1_20260914。父提交：df461b6c。范围：工程回归，无真实模型调用、训练、数据集版本或GitHub更新。

Agent级：未运行新的Agent验收，Strict/completed/mutation/模型终止统计不适用；不改变历史任务失败结果，不据此声称RWKV能力提高。角色级同样没有新模型结果。

## 已复现问题与根因

|问题|根因及影响|整改|验证|
|---|---|---|---|
|复制期间源文件改变仍启动模型|copytree没有前后身份比较，输入来源不可靠|共享复制函数检查源前、源后和副本；失败在模型启动前终止|RED.log→GREEN.log|
|权限修改没有计入变化|文件清单只有内容SHA|记录文件/目录类型、权限与内容身份，交付与changed_files使用树差异|RED.log→GREEN.log|
|集成丢失纯权限变化|内容差异为空就认为无需集成|当前内容集成明确拒绝纯权限变化|RED.log→GREEN.log|
|旧只读建议入口接受损坏父trace|配对检查仅在另一协助入口|共享父trace校验，同时检查存在的祖先生成记录|RED_RECOVERY_TREE.log→GREEN_RECOVERY_TREE.log|
|目录移动后残留旧空目录|集成只处理文件叶子，没有目录差异|按记录的树身份删旧目录、建新目录并验证最终树|RED_RECOVERY_TREE.log→GREEN_RECOVERY_TREE.log|
|缺少树身份的依赖仍准入|只有内容清单，无法认证权限与目录|依赖交付必须有final_tree，多父还要求INITIAL_TREE|RED_TREE_ADMISSION.log→GREEN_FINAL.log|

另有空目录变化显式拒绝回归：该测试在对应红阶段已经通过，是边界覆盖，不计为独立修复收益。最终新增七项测试，目标相关回归60 passed（21.51s）。

## 代码范围和上下游

workspace_snapshot统一身份与复制，不进入模型输入。coding_agent、assisted_agent保存SOURCE_COPY.json、INITIAL_TREE.json和final_tree；保留旧文件内容清单。read_only_agent与assisted_agent共用恢复trace配对检查。agent_integration要求可验证的依赖身份，保守合并同基线内容变化，结果仍交外部验收。

没有替RWKV选择工具、参数、业务方案或修改最终回答。目录变化现在也可能出现在changed_files中，调用方不能继续把它解释为仅普通文件列表。缺少树身份的旧交付不能直接进入新依赖集成，不自动补造历史证明。

## 验证与GPU约束

首次完整回归1678 passed（329.72s），日志为FULL_TESTS_BEFORE_EXPLICIT_GPU0.log。进程在核查时已自然结束，没有杀其他进程。Owner新增仅GPU 0约束后，显式使用CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES=0重新执行完整tests/；本轮最终结果以FULL_TESTS.log为准。未使用skip或排除必需测试。局部与完整测试顺序执行，避免共用pytest目录冲突。

本地nvidia-smi仅列GPU 0：NVIDIA GeForce RTX 5070 Ti，UUID GPU-7367aa85-43ac-ee32-6599-b8500f23bc48。环境限制只作用于本地子进程，不把它当作远端服务GPU配置证明；本轮未启动远端服务。

最终显式GPU 0完整回归：1678 passed，0 skipped，327.08s。GPU_ENVIRONMENT.txt来自运行中pytest进程环境核验；FULL_TESTS.log保存原始结果。源码和文档diff空白检查通过；纳入原始红日志后检查指出RED_RECOVERY_TREE.log第20行pytest原生输出的尾空格，为保留原始证据未改写该日志。

## 仍然存在的边界

- 三次树身份比较检测可观察到的复制期间变化，不是文件系统级原子快照，不能保证任意外部写入或改后恢复场景。
- 树身份未覆盖ACL、xattr、所有权、硬链接关系等完整文件系统元数据；当前支持范围是普通文件、目录及权限位。
- 多父集成拒绝纯权限、空目录和冲突，不做语义合并。独立任务调度仍按依赖波次等待，不宣称最优吞吐。
- 旧协助交付未记录final_tree时仅做原内容验证，不能认证历史权限；缺树身份的依赖集成则拒绝。单父检查至复制之间尚不是事务隔离。
- trace请求配对不证明native State数值正确。已有State/观察回归仍需保留。
- 编码纠正准入、失败/重试/强模型完整计费、远端峰值资源计量仍待完成；1万条仅为计划。

后续先完善纠正候选的来源与验证凭据，再补统一用量计账；完成工程边界后才继续真实trace。不得把工程/评分问题标为模型错误，也不直接把强模型接管输出当RWKV独立样本。

源码与报告SHA见SHA256SUMS；owner五处修改单独核对并不纳入提交。
