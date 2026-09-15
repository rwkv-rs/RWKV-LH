# R5 测试存储故障与清理

训练已正常完成225次更新，输出State加载校验通过。首轮测试72条记录中46次以model_transport_unavailable中断；该完整对比标记为基础设施无效，不计算为模型能力0分，也不以重跑抹去其资源消耗。

真实服务日志明确出现 `OSError: [Errno 28] No space left on device`，随后Torch State写入出现unexpected pos，创建请求返回503。现场根盘可用约34–39 MiB。较早的Unknown native state日志之后仍有成功import/create，不能仅凭该日志称State接错；当前确认的连续中断原因是磁盘写入失败。

owner授权删除过时内容后，仅清理两个已结束实验的临时State blobs：full-trace-runtime-r1-20260911与unified-train-r4-20260915/evaluation_state。共80,752,518,823 bytes（75.2066 GiB）；逐文件路径、字节数、SHA与删除后空间见DELETED_BLOB_MANIFEST.jsonl。相关journal、源码、模型、训练State、正式数据及日志保留。旧blob已不可用于二进制恢复，这项限制如实记录；没有删除当前R5失败State。

重测沿用原EVALUATION_REGISTRATION.json、模型、候选State、源码、任务、评分、采样与单题预算；重新运行全部72题次。只调整实验输出/State目录，并在模型传输不可用时停止批次。启动前要求本地存储至少60 GiB。没有修改生产模型输入、协议、评分或工具选择。存储空间预检及真实成功State写入作为本次运维修复验证，后续全组结果另报；未声称已解决长期自动State回收问题。

原R5 State另复制到NAS保全；NAS不支持保留mtime而导致cp非零，内容SHA核验结果见NAS_BACKUP_VERIFICATION.json。原始源文件未删除。训练候选已下载到本地data/models/statetune/direct-unified-r5-300-20260915/candidate.pth，SHA为0270c1190ae1b37d931dad86e4b3087ba98a99f1e27e33544fc2a7bb43d99582。
