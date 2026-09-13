# 会议资源预约服务

为内部会议室与设备提供可重启的 SQLite HTTP 预约服务。实现可维护的代码并更新本 README，说明启动、验证和数据持久化方式。可自行组织模块，不要求固定框架；运行环境提供 Python 3.11+ 标准库，不依赖联网安装。

公开启动契约：`python server.py --db /absolute/path/bookings.sqlite3 --host 127.0.0.1 --port 8080`。DB 父目录已存在；首次启动应创建数据库，后续启动保留数据。所有响应为 JSON，允许增加字段；所有接口从 URL 路由。

- `GET /health` → 200 `{"ok":true}`。
- `POST /bookings`，对象包含非空字符串 resource/customer、整数 start/end；start >= 0 且 start < end，bool/小数不是整数。时间单位为 UTC 整数分钟；区间为 `[start,end)`，首尾相接不冲突。同 resource 的 confirmed 预约不能重叠，其他 resource 不受影响。成功 201，返回 `{id,resource,start,end,customer,status:"confirmed"}`，id 为非空唯一字符串；冲突 409。
- `GET /bookings` → 200 `{"bookings":[...]}`，包含 cancelled，按 start、id 升序；可用 `?resource=...` 精确过滤，UTF-8 名称应保持原样。
- `GET /bookings/{id}` → 200 完整预约或 404。
- `DELETE /bookings/{id}` → 200 `{id,status:"cancelled"}`。重复取消幂等，取消后时段可被重新预约；未知 id 为 404。
- 非法输入、缺字段、坏 JSON → 400；失败不得改变任何预约。未知路由 → 404。错误对象含 error 字符串。

多个 HTTP 请求可以同时到达，冲突判定与写入必须为同一原子操作。终止并重新启动进程后，数据和冲突规则必须继续正确。公开验证仅是启动健康检查；请补充自己的行为验证，不能以健康检查替代完整功能。
