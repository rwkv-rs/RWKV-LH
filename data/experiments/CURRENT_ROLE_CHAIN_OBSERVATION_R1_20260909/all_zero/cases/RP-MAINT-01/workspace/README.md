# 旧版 SQLite 配置升级工具

这是已有的多模块 CLI 项目。用户反馈升级失败后 DB 被部分修改，重跑覆盖了可恢复备份。修复通用迁移、类型保真、备份和恢复逻辑，并补充验证与操作文档。升级/恢复在服务停机后运行，不要求与外部写进程并发。

环境为 Python 3.11+ 标准库；入口固定 `config_cli.py`。所有命令成功返回 0，并在 stdout 最后一行输出 JSON 对象；失败返回非 0，不得静默成功。

公开 v1 schema：`PRAGMA user_version=1; CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);`。value 是任意合法 JSON 值的 UTF-8 字符串。保留 key 和语义值，拒绝 NaN/Infinity/坏 JSON。还可能有无关用户表，必须保留。

v2 schema：保留 settings.key/value，新增 `value_type TEXT NOT NULL`、`updated_at INTEGER NOT NULL`；value 用 JSON `ensure_ascii=False, sort_keys=True, separators=(',', ':')` 规范化，类型为 `null/boolean/number/string/array/object`，迁移旧数据 updated_at=0。`PRAGMA user_version=2`，并有 `schema_migrations(version INTEGER PRIMARY KEY, description TEXT NOT NULL)` 的 version=2 记录。

- `python config_cli.py migrate --db DB --backup BACKUP`：只允许 v1→v2。首次必须先保留有效的完整 v1 SQLite 备份，再原子发布升级；BACKUP 不得等于 DB，已有备份不得覆盖。成功输出 `{from_version:1,to_version:2,migrated_rows:N,changed:true,...}`。已为 v2 时返回 changed=false、from_version=to_version=2、migrated_rows=0，且不改 DB 或备份，即使 BACKUP 已存在。
- 任一坏 JSON、未知版本、冲突备份、异常 schema 或恢复失败都必须失败，原 DB 字节保持不变；不能丢失原行、表或版本。无关用户表保留；已有不兼容 schema_migrations 不得强制删除或覆盖。
- `python config_cli.py list --db DB`：返回 `{schema_version,settings:[{key,value,value_type},...]}` 按 key 排序，value 为解码后的 JSON 值。
- `python config_cli.py get --db DB --key KEY`：返回对应 `{key,value,value_type}`；未知 key 非 0。get/list 支持合法 v1、v2；不得修改 DB。
- `python config_cli.py restore --db DB --backup BACKUP`：验证备份确为完整合法 v1/v2 配置 DB 后原子恢复，返回 `{restored:true,schema_version:版本}`；损坏文件、非配置 SQLite、缺失文件应失败并保留原 DB；不得修改 BACKUP。

DB/backup 父目录已存在。允许调整内部模块，所有运行数据路径由 CLI 指定。`sample_v1.sql` 是小样例，不代表全面输入。请实际验证正常升级、重跑、坏数据回滚、恢复和 Unicode。
