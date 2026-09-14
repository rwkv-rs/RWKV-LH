首遍全量1717 passed/3 failed，不能算通过。执行失误：全量运行期间又启动定向pytest，仓库固定--basetemp=data/test_runs/pytest，后启动的pytest清理了前者仍使用的临时目录。三项失败均为该目录SQLite unable to open/disk I/O，不是训练或State模型结果。同时期间有新增代码/测试，首遍也不能代表最终源码。原日志完整保留；停止并行测试，最终源码固定后仅运行一遍完整回归，不修改失败用例或SQLite逻辑来规避。

第二遍1723 passed/1 failed：运行期间补了快照封存检查，测试冻结源清单后coding_corrections.py SHA发生变化，来源身份保护正确拒绝。该遍也不代表最终源码。此后代码与测试固定，再运行最终完整回归；保留FULL_TESTS_SOURCE_CHANGED.log。定向补测使用独立basetemp，不再共享目录。
