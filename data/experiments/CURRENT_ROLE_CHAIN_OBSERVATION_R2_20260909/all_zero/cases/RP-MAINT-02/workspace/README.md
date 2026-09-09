# 增量文档索引维护

这是已有的多文件 Python SQLite 索引工具。用户报告子目录文档找不到、删除文件仍出现、相同时间戳内容变更被忽略，以及 Unicode 查询不一致。修复通用扫描/增量更新/查询/持久化路径，保持 CLI 接口，说明验证方法。可调整内部模块；不需要外部包或在线服务。

Python 3.11+ 标准库，入口 `index_cli.py`。成功退出 0，stdout 最后一行 JSON 对象；非法输入或损坏数据非 0。所有运行 DB 路径由参数指定。

- `python index_cli.py sync --root DOCS --db DB`：递归索引 DOCS 下扩展名为 .md/.txt 的 UTF-8 普通文件（扩展名不区分大小写）。相对路径用 POSIX `/`；跳过符号链接文件和目录，不读取链接指向的外部数据。文件名、内容保持 Unicode。忽略其他扩展名。
- 同步按内容变化识别更新，mtime/size 相同也可能变化；文件删除应从索引删除。返回 `{added,updated,deleted,unchanged,generation}`，按文件计数。generation 从 0 开始，只有新增/内容修改/删除时加 1；纯重复同步不增加。
- 一次扫描中任一目标文件不能严格 UTF-8 解码或发生读取错误，整次同步失败，已有文档/查询结果/代数不能部分更新。不存在的 root 失败。一个 DB 绑定首次 root 的绝对路径，不允许换 root 后静默混用。
- `python index_cli.py query --db DB --text TEXT`：非空查询，对内容进行 Unicode NFC 规范化后 casefold 的字面子串匹配；TEXT 同样处理。`Straße` 应匹配 `STRASSE`，组合/分解的 é 等价。返回 `{count,matches:[{path:相对路径},...]}`，每文档一次，按路径升序；没有匹配返回空数组。禁止把 SQL 通配符或正则表达式当作查询语法。
- `python index_cli.py status --db DB` → `{document_count,generation,root}`；query/status 不修改索引，不存在 DB 应失败。

进程重新执行后仍应保留原索引，不要求源文件在查询时仍存在。样例 docs 只用于手工演示；请实际验证增删改、同时间戳、Unicode、坏文件原子失败和重启。更新 README 操作说明。
