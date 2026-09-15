# R9：完成下载恢复，实际Coding管线后台启动

任务级：本轮新准入并启动1个Loguru公开仓库重新实例化任务，RWKV实际generation_started已核验。提交、合格交付和mutation尚不在启动时断言；不是项目Strict。配置并发4，但本批只有1题，有效并发1，不把源记录数或静态审计数当成执行数。当前无教师、无训练。

## 下载与来源索引

7分片14,893,550,932字节全部通过完整LFS SHA与大小核验，结构审计共69,895条，源JSON解析invalid_rows=0。首次4分片curl退出18，已有3分片29,895条审计完成；普通续传仍失败，原STATUS和日志保存在R8/recovery_01。独立32-byte Range探针确认新偏移查询返回正确Content-Range，恢复脚本在原固定源URL添加resume_offset以刷新请求，保留partial逐步续传，完整SHA通过才更名。2、3分片中途再次退出18，随后从实际新偏移继续成功，所有尝试保存在RESUME_EVENTS.jsonl。没有丢弃旧错误或降低校验。

全量索引69,895 UUID：codex 29,894、claude 19,769、cursor 7,422、mini-swe-agent 12,810。非空主需求按空白规范化有45,763种摘要、11,287组重复；这不是语义去重或已可复建独立任务数。SOURCE_RECONSTRUCTION_INDEX逐行保留来源路径、offset、字节SHA、目标提取拒绝及用户中的仓库/commit线索；未知环境均待复建，索引不会自动放行。

## 第一批真实任务

来源Code_Agent_000009原PR需求：Loguru在Cython/atexit等栈帧不足环境中崩溃。原业务描述逐字保留，旧上传环境/源Harness步骤包装替换为真实说明。公开0.7.0 tag解析到commit `9fc929a54ae6ef92208c90ebafd449b8f9e3e34a`，官方archive原样下载，未从教师补丁反造源码；原采样私有测试不可用，不能称原环境恢复。

真实Python3.13的atexit已复现ValueError；注意它进程exit0但stderr含异常、消息未输出，验收不会只看exit码。普通日志对照通过，模拟get_frame不可用用例失败；模拟不等于真实Cython编译验证。只读隔离验收预演得到相同结果，公共level/bind测试57 passed。模型工作区保留公开源码与测试，加冻结依赖/运行器/真实环境说明，私有探针及评分留在工作区外。

生产convert_task/preview_input及正式队列入队检查已通过；无engineering-inventory绕过。24调用、1200秒/任务，全批1小时，zero State，GPU0，新GC服务身份，配置并发4。预算允许模型自主选择读取、修改、测试及回答；程序不代选动作/补参数/改答案。当前1题尚未扩为3万任务，后续须继续复建其他来源，不能启动静态轨迹重放凑数。

## 后台行为和查看

WSL用户unit：`rwkv-lh-coding-collection-r9.service`。它执行已冻结真实任务队列，落盘收据，再自动重建完整输入/token/State/生成前快照、核对首输入与preview，并在只读隔离副本执行3项错误路径检查和57项公共测试，核验受保护文件。工具或传输中断保留失败，不自动重做未知模型请求。代码检查结果与最终回答人工验收分开，后者不自动打合格。

```bash
systemctl --user status rwkv-lh-coding-collection-r9.service
cat /home/chase/GitHub/RWKV-LH/data/experiments/RWKV_COLLECTION_DEPLOY_R9_20260915/PIPELINE_STATUS.json
/home/chase/GitHub/RWKV-LH/.venv/bin/python /home/chase/GitHub/RWKV-LH/scripts/run_collection_queue.py --queue /home/chase/GitHub/RWKV-LH/data/experiments/RWKV_COLLECTION_DEPLOY_R9_20260915/queue.sqlite3 --status
```

实时输出pipeline.log；真实收据converted/run/COLLECTION_RECEIPT.json；边界证据boundaries；结束后外部结果post_run_checks/CHECKS.json。--status结果中的模型计数仅已落盘任务，不能把在途任务的0误读为没有调用。强制停止用`systemctl --user stop rwkv-lh-coding-collection-r9.service`，在途项可能需要按原队列未决恢复规则处理，不盲目重启。

按owner最新要求，只确认启动，不再持续监测、不设置定时消息；owner会后自行检查。该worker和SSH隧道在WSL，WSL须保持运行，远端Native服务只用GPU0。源码和协议未修改，已有1870全回归通过；本轮验证是下载身份、原问题复现、57公共测试、隔离探针和正式转换/真实启动，不新增训练数据标签，不push。五个owner修改保持。R8“自行检查/不监测”曾被临时监测授权覆盖，当前又以本条部署后停止监测为准。
