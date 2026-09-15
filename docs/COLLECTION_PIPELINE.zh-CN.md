# 真实 Agent 采集管线

目标是 30,000 个独立、可复建任务的真实执行；不是 30,000 条参考回答，也不是自动入训。优先 SFT-Agent 和项目真实来源，RL 代码/长文任务补充。当前只实现队列和来源结构审计基础，尚未冻结 3 万题或启动大批模型执行。

## 当前入口

`scripts/audit_collection_sources.py --source /absolute/source.jsonl --revision PINNED_REVISION --output /absolute/audit.jsonl` 按行扫描 SFT-Agent，保存原始字节偏移、行 SHA、协议结构观察。结构合格不代表环境复建或参考回答正确。

`scripts/run_collection_queue.py --queue /absolute/queue.sqlite3 --inventory /absolute/admitted.jsonl` 事务性纳入已复建且事前登记验收的任务，失败整次回滚。

每行需包含 source_id、source_path、source_sha256、environment_sha256、acceptance_path、acceptance_sha256、job。source_id 必须绑定数据集修订与原题身份，不使用生成调用编号；近重复家族切分仍须在上游完成。source_path 是保留的原始行文件；acceptance_path 是外部验收约定，两者在工作区之外，不传给模型。

环境摘要算法为 `SHA256(json.dumps(tree_identity(workspace, allow_links=False), sort_keys=True, ensure_ascii=False, allow_nan=False).encode())`。实际运行前重新验证三个摘要，拒绝冻结后改变的来源、验收或工作区。

job 字段严格为 task_id、request、workspace、output_dir、tool_scope、max_calls、max_seconds。tool_scope 仅 files / inspect / coding。拒绝 assistance、on_stall 等附加选项，不接强模型。

`--run --concurrency N` 使用生产直接 Agent 入口有界分批执行，只允许 zero State，保存无密钥的运行参数并拒绝恢复时变化。默认磁盘保留 20 GiB，`--min-free-gib` 可提高。运行前仍必须完成下列部署门，不能据此入口直接宣称已经具备 3 万题运行条件。

## 任务状态

pending → running → recorded。recorded 仅指原始执行结果已落盘，不代表成功，不是训练准入。

SQLite WAL/FULL 和事务领取避免重复领取；进程锁防止两个队列主进程同时启动。中断后 running 不自动重跑，须核验真实 trace、Native 请求收据及 State 身份；当前没有自动恢复 running 的入口，避免未知执行被重复计数。保留原始任务失败，不自动纠正答案。

## 大批运行前尚需完成

1. 固定修订扫描 SFT-Agent，定位可复建的源码版本及初始材料；不从未来回答反造初始环境。对不可复建项记录具体缺项。
2. 上游完成跨来源相似任务去重、任务家族隔离及验收器绑定。现入口已检查全库存任务 ID、输出路径及跨批源目录重叠，但不能替代语义去重。
3. 冻结模型、tokenizer、协议、完整部署源码 manifest、采样、任务预算和验收。现有参数快照不是完整源码 attestation 的替代品。
4. 独立小批核验精确输入、输出 token、观察和 State 谱系；当前生产轨迹保存仍需证明满足大批恢复要求。
5. Native 服务全局请求锁覆盖生成且使用共享 active_request_id；不得直接删锁。先测串行瓶颈与 State 隔离，再决定工程改动或稳定并发值。
6. 完成任务级 State 释放、磁盘多卷水位和故障回压；当前只检查队列所在卷，尚不监控远端 State 卷。
7. 外部验收结果与原始提交分开存储，跑后分类。现队列不执行隐藏验收、不自动产出错误标签。

只使用 GPU 0。本轮无教师纠错、无训练；保留成功和失败原始轨迹。当前 12 题固定回归及衍生内容不进入未来训练，最终 holdout 不读取。
