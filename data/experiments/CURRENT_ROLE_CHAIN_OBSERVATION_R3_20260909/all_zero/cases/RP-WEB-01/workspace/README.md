# RP-WEB-01

为小团队从零创建可持久化 Kanban 任务板。任务包含标题、描述、优先级 low/medium/high 和 todo/doing/done 状态。支持新增、编辑、状态移动、删除，标题必须去除首尾空白后非空；无效提交显示 role=alert 错误，不改变任务。搜索标题或描述（大小写不敏感），并与状态、优先级筛选相交。使用语义化表单和按钮，键盘 Enter 可提交新增、激活状态移动，不得只支持拖动。
公开 UI：字段名称 Task title、Description、Priority；新增按钮 Add task；Edit 将内容载入编辑器，Save task 保存，Cancel edit 取消。筛选字段 Search tasks、Status filter(all/todo/doing/done)、Priority filter(all/low/medium/high)。每张卡为 article，可访问名称 `Task 标题`，显示描述、状态、优先级；按钮 Edit、Delete 和各非当前状态的 `Move to todo` / `Move to doing` / `Move to done`。
运行方式：项目根目录提供 index.html，可由 `python -m http.server PORT --bind 127.0.0.1 --directory WORKSPACE` 服务。浏览器初始没有数据；使用 localStorage 持久化，刷新保留所有已提交变化。初始目录仅有需求，需实现页面和逻辑。

交付时保持工作区为自包含项目，README 说明启动与人工验证方法。不得依赖远程 CDN、外网或需要下载的包。页面使用英语可访问名称以方便协作测试；允许任意视觉设计与代码组织，但下列公开交互合同保持稳定。通过真实浏览器操作检查行为，不以 CSS 长度或源码关键词验收。

