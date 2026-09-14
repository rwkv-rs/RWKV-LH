# RWKV_NATIVE_GC_EMPTY_QUEUE_R1_20260914

任务级：真实产品 CLI smoke 1/1，通过已有递归检查并忠实回答；submitted 1，mutation 0，answer_submitted。不是项目 Strict、训练收益或并发收益。默认 zero State，未部署 NO_KEEP 候选。

生成级：2 次完整精确重放，逻辑输入 8842 / 输出 155 token，协议拒绝 0。真实工具执行及全文输出、State 关系保存在 EVIDENCE.tar.gz；端到端 8.542 秒（CLI 进程总耗时 9.554 秒）。

根因：reclaimable_store_keys 在 GC 队列为空时仍解码并核验全部历史 State。原服务实际 journal 有 8409 个 State；只读一致事务探针，旧函数 9.277 / 8.422 秒，新函数 0.00004171 / 0.00000662 秒。数字仅代表空 GC 查询函数，不能换算项目加速比。新服务使用独立空 journal，也不能与旧服务直接比较端到端收益。

修复：先查询待回收键，空队列直接返回；非空队列原完整性、存活 owner 和 pending pin 保护原样保留。没有修改模型输入、参数或答案。5000 历史 State 的 SQLite 指令预算回归先红后绿；非空队列损坏元数据仍拒绝。针对性 104 passed；全套 GPU0 1758 passed、0 skipped，327.07 秒。

新服务仅 GPU0，源码完整清单冻结上传，服务器未调用 Git。首次部署误配空 profiles 清单被已有校验拒绝；改用既有 zero_only 默认，失败日志保留。旧服务未改动；两个模型同时驻留的资源不算并发优势。初次只读探针漏配 Row factory 的失败也保留，属于探针错误。

边界：非空 GC、release/alias 路径仍可能扫描历史；历史 State 保留策略未改变。不能称 State 服务全部性能问题已解决。Owner 五处修改 diff SHA 314ca524bbb1e4fc28460409f1068222f29f1819cb410d025edefe64c8f796e0，未混入提交。完整源码快照 deployment/source 留本地，不打包 owner 修改；源码 manifest 入证据。
