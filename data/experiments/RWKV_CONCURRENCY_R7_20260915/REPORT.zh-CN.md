# R7：并发实测与默认服务性能修复

## 任务级结果

旧服务8/8、修复后同组8/8、扩展负载48/48均按运行前登记的工程目标通过；64次均RWKV独立提交，mutation=0，均answer_submitted，协议/传输/State重建错误0。这里始终只有两个历史公开检查目标反复执行，不是64个新题，不是项目Strict，不计入3万条采集。实际命令、输出与原始最终回答分开核对；没有把submitted直接等同合格。数字输出的末尾换行展示省略不构成实质事实改写。

## 性能结果

|固定负载|并发|两遍批次耗时（秒）|
|---|---:|---|
|修复前：2任务|1|138.10 / 141.46|
|修复前：2任务|2|135.35 / 137.18|
|修复后：2任务|1|18.01 / 15.58|
|修复后：2任务|2|13.00 / 13.61|
|修复后：8任务|2|47.28 / 46.55|
|修复后：8任务|4|43.76 / 43.38|
|修复后：8任务|8|44.11 / 44.08|

同并发2的修复前后，平均136.26秒→13.30秒，约**10.24倍**。这是部署空GC快速返回的收益，不能称为GPU并行收益。修复后的2任务组，客户端并发2相对串行约1.26倍，含首批缓存冷启动差异，样本不足以外推。

8任务同负载中，并发4两遍均快于2，约7.7%；并发8没有超过4。当前同类短任务建议显式`--concurrency 4`，不盲目继续加worker；这不是最大稳定并发认证，不能把此耗时外推到真实仓库修复。2任务组走带纠正快照的生产采集队列；8任务组走生产agent_batch负载入口，重复任务不绕过正式采集去重，默认不采生成前纠正快照。仅在各自相同入口内比较并发，不把两种负载直接相除。

## 已确认根因及部署

线上Native服务仍加载旧native_request_recovery：即使native_state_gc为空，每次RPC也扫描并解码全部历史State。部署前8506条State、11602条请求全部completed、待GC为0；没有在途请求。远端原文件复现回归1失败/1通过（SQL扫描预算耗尽），本地修复2通过。非空队列的完整性/引用保护保留。此前R1已有修复但仅部署到独立服务，恢复默认服务时又使用了慢版本。

先核验旧完整132文件清单，再仅替换`rwkv_lh/runtime/native_request_recovery.py`，在本地生成新完整清单上传。新清单SHA：`1f29962fde1f7592d43d39b89a471e80afb84b074e9ca08d1a8be4c5b642b11e`。engine、权重文件、16K上下文、采样、1800输出预算、GPU0、8槽State缓存及原历史日志/State目录均保持。server_build随源码身份改变，因此使用新的served-model别名`rwkv7-g1j-13.3b-zero-state-capability-ctx16384-gc-r7`，避免旧create收据指向不兼容State；未修改旧State身份或删除历史日志。服务启动前完成manifest验证。默认unit通过独立drop-in指向新freeze，本地.env.local仅调整模型别名，其余配置保留。

修复前后8对首轮实际模型输入逐token相同。输出采样有措辞差异，逻辑后续输入随真实输出变化，不能宣称所有token完全相同。同目标初始State有幂等缓存，修复后首create属于新身份冷启动；没有用空日志冒充公平性能对照。新旧源码各自的并发两臂均冻结未变。

## 角色与轨迹数字

|组|生成|逻辑输入token|原始输出token|
|---|---:|---:|---:|
|baseline|16|60855|1190|
|post_fix|16|60826|1159|
|scale|96|365073|7310|

128/128生成输入通过唯一生产构造函数重建，完整输入、原始输出/精确token、真实工具结果、父子State及终止原因已保存。前后对照32边界额外核验生成前快照。负载组144个非根native State引用跨任务无重复；重复目标可共享不可变初始缓存，各执行子State隔离。所有本轮Native请求均有completed持久收据。原始GPU0遥测保留，覆盖含启动和空闲，基线首段缺失；不据此计算公平总能耗/费用。未调用教师、未训练、未新增数据集版本。

## 尚未解决的并发瓶颈

`native_state_service.dispatch`经全局request_lock执行；generate还持有全局self.lock。共享_active_request_id、State缓存逐出和export/commit/rollback的原子关系依赖当前串行保证。只提高vLLM max_num_seqs或删除锁均不等于安全并行。当前已配置max_num_seqs=16，仍有这层限制。

下一轮分两条工程工作推进：
1. 冻结两个不同父State的并行生成、共享父分叉、重试/取消、commit/rollback、缓存压力回归；先证明当前请求串行，再实现请求上下文隔离与State引用级同步/活跃缓存保护，验证真实GPU批处理和吞吐。不能仅移除全局锁，不添加模型决策角色。
2. SFT真实仓库任务继续绑定来源、初始环境和私有验收，先补不同任务试采，用真实Coding负载复测并发。当前AnyIO一题试采及115来源审计不等于3万可运行环境，重复工程目标不凑数。

## 验证、保留与恢复

本轮完整GPU0回归1870 passed、0 skipped（357.78秒）；专项91 passed，旧GC回归红→绿。五处owner修改SHA未变，未纳入提交；无GitHub更新、无训练，服务器未使用Git。新快速默认服务已保留，只有GPU0使用。源码完整清单、启动原参数、服务身份和override保存在deployment，原始旧源码也仅作为本轮部署对照证据封存。

需要恢复旧身份时先确认所有任务已结束，然后停止同一user unit，删除本轮`rwkv-lh-native-current.service.d/concurrency-r7.conf`，daemon-reload并启动原unit，同时将本地模型别名恢复为不带`-gc-r7`的原值。原启动脚本未改，旧日志未删；旧版会恢复已确认的性能问题，不能默认回退。systemctl使用UID1001的XDG_RUNTIME_DIR和DBUS_SESSION_BUS_ADDRESS，禁止调用服务器Git。

证据：REGISTRATION.json/post_fix/REGISTRATION.json/scale/REGISTRATION.json为各阶段事前冻结；TASK_REVIEW.json、SCALE_REPLAY_REVIEW.json和RESULTS.json为审核；EVIDENCE_INDEX.json与EVIDENCE_BLOBS.tar.gz保存逐文件SHA和原始工件，SHA256.json记录根级材料校验。重建与后续核验不得将这些重复冒烟结果准入正式3万条或当作训练标签。
