# RP-FULL-01

为小团队从零实现工单支持台，包含 HTTP API、SQLite 与可操作网页。用户创建带标题和描述的工单，初始 status=open、assignee=""；可分配负责人、关闭工单、搜索和状态筛选。空白标题拒绝。更新必须原子校验，非法 status 不得顺便修改 assignee。
API：GET /api/tickets?q=文本&status=all|open|closed 返回 {"tickets":[{"id":唯一值,"title":文本,"description":文本,"assignee":文本,"status":"open或closed"}]}；q 在标题/描述做大小写不敏感子串搜索。POST /api/tickets 接收 {title,description} 并返回新工单。PATCH /api/tickets/ID 接收 assignee 和/或 status，返回更新工单；status 仅 open/closed。
公开 UI：Ticket title、Ticket description 字段和 Create ticket 按钮；Search tickets 与 Status filter(all/open/closed)。每工单 article 名称 `Ticket 标题`，展示描述和状态，内部 Assignee 字段、Assign 按钮；open 工单有 Close 按钮。
运行方式：`python server.py --host 127.0.0.1 --port PORT --db PATH`，仅用 Python 标准库与原生浏览器功能；数据库 PATH 由运行者给定。源码目录运行时可只读，数据库及运行文件写入 PATH 所在临时目录，不能写回源码。GET / 提供页面，SQLite 持久化，停止服务再用同一个 PATH 启动后数据不丢失。所有 API 接受/返回 JSON，成功创建 HTTP 201、查询/更新 200；无效输入 400、缺失资源 404；返回错误对象含 error。id 为稳定唯一值，多个独立浏览器看到相同服务数据。

交付时保持工作区为自包含项目，README 说明启动与人工验证方法。不得依赖远程 CDN、外网或需要下载的包。页面使用英语可访问名称以方便协作测试；允许任意视觉设计与代码组织，但下列公开交互合同保持稳定。通过真实浏览器操作检查行为，不以 CSS 长度或源码关键词验收。

