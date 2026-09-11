# 先诊断，再修复

库存流水聚合已有可运行模块，重复SKU的数量出现回归。stock_totals(entries)接收(sku, signed_quantity)可迭代对象，逐SKU累加所有正负流水，并按首次出现的SKU顺序返回(sku, total)列表；零总量也必须保留，输入不可被修改。

项目已安装所需pytest，当前恰好一个测试失败。先执行 `python run_tests.py` 观察真实失败，再修复实现，最后再次执行同一命令使pytest退出0。不要修改tests、run_tests.py或添加pytest/conftest遮蔽测试；不得手写或伪造测试报告。run_tests.py调用实际pytest，原样打印输出、返回pytest退出码，并把输出和源文件SHA写入TEST_REPORT.md。初始失败是待诊断事实，不能声称测试通过。需要持久化报告的命令必须在可写的工作区运行；只读检查产生的文件不会保留。

验收：实现满足上述通用规则；先失败后成功的实际命令记录；原tests和run_tests.py保持不变；TEST_REPORT.md包含实际pytest输出、Exit code: 0与当前源码SHA。不要只描述建议，提交修复后的项目和报告。
