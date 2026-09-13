# RWKV_INPUT_GENERATION_BOUNDARY_FIX_R1_20260913

本轮仅修复已复现的输入轮次结构，不报告新的任务通过率或模型收益。上一轮任务3/8、提交3/8、mutation0、5次预算终止仍是历史基线，不能拿源码修改后未经对照的结果冒充收益。用户要求继续推进自主文档问答与bug检查，后续真实运行会使用修复后的同一生产构造器。

## 结构修复

候选回滚到生成输入checkpoint时，末尾仍有运行时生成的空JSON开头。追加新的User观察必须先结束这个空开头；不能仅凭事件类型判断，因为protocol_rejection也可能发生在已经commit的完整输出之后。

- `model_io.py` 在统一事件与rollover摘要构造函数中接收上一段transcript，仅对两个当前canonical空生成开头补协议闭合符。没有填JSON、参数、工具选择或答案，没有恢复被拒绝候选为有效操作。
- `model_session.py` 的prompt replay/native两种append、fork和rollover均传入真实上文。原checkpoint不修改，新字节作为真实child State输入；自然提交的原始回答不改变。
- `direct_trace_data.py` 用同一构造器和真实父checkpoint重建观察字节，生产与后续数据通道保持一致。
- `model.py` 的输入预留估计也传入上文；native实际append预算按新增真实字节计算，预算不足在发给服务前拒绝。

## 回归证据

修正后的同一测试在已冻结的旧源码上得到8 failed、2 passed，见RED_FROZEN_SOURCE.log：失败覆盖两种生成开头、native/replay、连续事件、fork、rollover；正常已闭合提交作为对照通过。第一次RED.log中另有两个测试夹具未模拟完整Markdown外壳导致解析失败，保留原记录，修正夹具后才记录上述有效红测，未修改生产parser放宽接受。

新边界回归11 passed（含真实新增token预算边界）；模型会话/Controller相关组合110 passed；最终全量1569 passed、0 skipped，298.91秒。全部日志保留。尚未以新真实模型运行证明任务质量收益；解析失败反馈缺少finish_reason及失败原文、搜索策略等问题没有捆绑修改。

## 保留已有修改

原owner在model.py新增的start_atomic_actor_state方法完整保留，本轮仅暂存此前token预算位置的两个独立修改。其他四个owner修改文件SHA不变。本轮生产变更不提交owner原有差异。无训练、新数据集版本、GitHub更新或服务器Git操作。

## 下一步

真实文档问答与代码缺陷检查以用户追加目标开展，借鉴rwkvrag的原文来源坐标/哈希、独立任务并发和证据后作答；先保留小任务直接RWKV执行。不把原文材料自动改写成答案，不引入强模型逐步审核关卡。原4题8次搜索定位门未通过，不据此宣称通用仓库定位已稳定。串行与并发的质量、耗时和所有失败成本分别记录。
