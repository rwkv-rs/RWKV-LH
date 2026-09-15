# R8 后台来源准备已启动（尚非3万Agent任务执行）

任务级：新增RWKV任务0，合格交付0，mutation0，教师/训练0。R7的64次工程执行全部通过，仅两个历史目标的重复负载，不计正式采集。

已按owner的后台运行授权，在WSL UbuntuRecovered部署`rwkv-lh-sft-source-r8.service`，4路并发下载固定修订的7个SFT Code分片，共14,893,550,932字节。启动核验已观察到4个下载文件真实增长；快照见LAUNCH_VERIFIED.json。该进程独立于本次对话继续运行，不设置Codex定时监控。WSL与本机代理必须保持运行；这不是已部署到远端服务器的采集进程。远端GPU0的快速Native推理服务另已常驻。

本后台任务自动执行：固定分片下载（最多3次网络重试）→完整大小及LFS SHA匹配→调用已有生产来源审计函数→每分片保存原始JSONL、结构分类、恢复检查点和终止状态。四路并行，总时限36小时；全部分片结束后自动退出。源码使用独立冻结副本，主工作区后续代码变更不会混入该次审计。下载失败/不匹配的原始文件和日志保留，不进入后续审计；不循环重复执行RWKV题目、不删除失败。

此阶段分类限源协议/工具定义/消息结构/loss mask等，不能称为RWKV错误分类。环境、业务目标、私有验收和本地协议转换仍须复建核验，所有源记录默认未准入。不会直接把静态对话当作生产trace送训，也未宣称3万个可执行环境就绪。

部署验证：使用一条已有真实源行，完整SHA正确时通过原来源审计，篡改期望SHA时明确失败且没有audit产物；最终冻结副本再次通过这两种情况。生产源码未改，沿用刚完成的1870项全绿回归。首次后台启动未继承WSL代理，HF直接连接超时，随后显式接入已有127.0.0.1:10808代理，原错误日志保留；修正后已核对真实下载字节。零模型调用，未抹除任务失败。

## 自行检查

在WSL执行：

```bash
systemctl --user status rwkv-lh-sft-source-r8.service
cat /home/chase/GitHub/RWKV-LH/data/experiments/RWKV_SFT_BACKGROUND_R8_20260915/STATUS.json
```

分片进度见`Code_Agent_part-*/STATUS.json`，下载大小看对应`source.jsonl.download`。审计进行时看`audit.jsonl.checkpoint.json`，最终结果是`audit.jsonl`。总STATUS在全部分片结束后更新，异常终止时应同时以systemd状态为准。模型执行数明确为0，不能将source_rows当作真实Agent采集数。

停止：`systemctl --user stop rwkv-lh-sft-source-r8.service`。手动再次start会核验同一freeze，续传partial并恢复已审计检查点；不是自动重试未知模型请求。完成所有来源审计后仍需要环境复建与正式任务冻结，才能启动并发4的真实采集。

后台不会自行更新GitHub、启动训练或调用教师。所有Git仅本地进行。R7快速服务与本轮来源准备分开登记，不把后台进程active状态当作数据有效或工程问题全部解决。
