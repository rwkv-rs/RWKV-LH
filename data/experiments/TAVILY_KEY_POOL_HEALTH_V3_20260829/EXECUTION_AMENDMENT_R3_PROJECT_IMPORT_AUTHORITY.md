# V3 R3 项目导入权限修正

登记时间：2026-08-29；发生在 R3 任一外部调用之前。

R3 的两次前置条件尝试均在发出网络调用前以 `17 != 29` fail closed，且未创建 R3 结果目录。根因是直接执行 `temp/` 脚本时未显式设置项目 `PYTHONPATH`，Python 可解析到环境中已安装的旧 RWKV-LH settings，其默认 env authority 不是当前工作区文件。`python -c` 从工作区导入时已复核当前正式 loader 读取 29/29 唯一值。

实际 R3 调用固定增加 `PYTHONPATH=/home/chase/GitHub/RWKV-LH`，并保留清除继承 Tavily 变量的条件。脚本、探测、分类、顺序、次数、门槛及输出目录均不改变；启动后脚本仍先执行 29-key 断言，失败则零外部调用。

