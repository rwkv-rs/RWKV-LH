# 库存与订单服务

给小型仓库实现 SQLite HTTP 订单服务，解决网络重试重复扣库存及多行订单部分扣减问题。实现可维护代码并更新 README 的启动、验证和事务说明。允许自行组织模块；Python 3.11+ 标准库可用，不需要联网依赖。

启动：`python server.py --db /absolute/path/inventory.sqlite3 --host 127.0.0.1 --port 8080`。首次创建 DB，重启保留数据；所有响应 JSON，可增加字段。

- `GET /health` → 200 `{"ok":true}`。
- `PUT /inventory/{url-encoded-sku}`，`{"stock":N}` 设置该 SKU 当前可售量，创建或更新返回 200 `{"sku":...,"stock":N}`。N 必须非负整数，bool/小数非法。SKU 为非空 UTF-8 字符串。
- `GET /inventory/{sku}` → 200 对应库存或 404。
- `POST /orders` 必须有非空 `Idempotency-Key` 请求头（最长 128 字符），JSON 为 `{customer:非空字符串,items:[{sku:非空字符串,quantity:正整数},...]}`。同 SKU 的重复项数量求和，再按 SKU 排序；item 顺序和重复项拆分不影响语义。quantity 不接受 bool/小数。
- 首次成功返回 201 `{id,customer,items:[规范化明细],status:"confirmed"}`；同 key、相同规范化请求返回 200 同一订单，不再次扣库存。同 key 不同 customer/明细返回 409，不修改状态。
- 任一 SKU 不存在 → 404，任一数量不足 → 409；失败应整体无写入，不扣其他 SKU、不创建订单、不占用 key，允许之后更正请求重试。
- `GET /orders` → 200 `{"orders":[...]}` 按 id 排序；`GET /orders/{id}` 返回 200 完整订单或 404。
- 坏 JSON、非法字段、空 items/key → 400，错误对象含 error。非法请求不得改变库存或订单；未知路由 404。

库存判定、扣减和订单/idempotency 登记必须原子完成。并发相同 key 只创建一单；并发不同 key 不得超卖。库存、订单、key 在进程重启后继续有效。公开验证只做健康检查，请自行补充交易与恢复验证。
