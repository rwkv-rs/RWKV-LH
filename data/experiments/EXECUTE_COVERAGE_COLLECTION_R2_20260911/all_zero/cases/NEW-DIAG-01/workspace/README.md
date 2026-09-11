# 先诊断，再修复

缓存策略模块已有可运行实现，但时间边界出现回归。缓存只在 age < ttl 时有效，恰好到期或超过到期必须过期；负TTL和倒退时钟必须抛ValueError。保留is_fresh(created_at, now, ttl)接口。

项目已安装所需pytest，当前恰好一个测试失败。先执行 `python run_tests.py` 观察真实失败，再修复实现，最后再次执行同一命令使pytest退出0。不要修改tests、run_tests.py或添加pytest/conftest遮蔽测试；不得手写或伪造测试报告。run_tests.py调用实际pytest，原样打印输出、返回pytest退出码，并把输出和源文件SHA写入TEST_REPORT.md。初始失败是待诊断事实，不能声称测试通过。需要持久化报告的命令必须在可写的工作区运行；只读检查产生的文件不会保留。

验收：实现满足上述通用规则；先失败后成功的实际命令记录；原tests和run_tests.py保持不变；TEST_REPORT.md包含实际pytest输出、Exit code: 0与当前源码SHA。不要只描述建议，提交修复后的项目和报告。
