# Planner 请求格式离线核对 · A / R2

三次请求的外层格式一致，现有证据没有显示客户端请求格式错误。API01 的第一次请求成功，API02 的首次请求采用同样 system prompt、同样字段，体积更小却返回 500；这不支持“只因修复 prompt 太长”或“这些固定字段一律不被上游支持”的解释。500 的提供方内部根因仍不能由客户端记录单独确定，也不能排除内容触发或路由相关的上游缺陷。

本诊断没有重发请求。脚本禁用了 `requests.Session.request` 和 socket connect，只读取原有 trace、公开 workspace 和冻结源码，在 HTTP 层之前离线截获并组装请求。未读取隐藏验收、reference 或数据库，未修改运行配置、生产代码或评分。

| 请求 | 结果 | user 字符数 | system 字符数 | 重新编码的完整 JSON body 字节数 |
|---|---|---:|---:|---:|
| API01 初始 `SUP-8069342ba94e4fc69692` | 成功，1 次 HTTP | 1,360 | 6,486 | 8,585 |
| API01 修复 `SUP-9d719be01df5484fb546` | HTTP 500，2 次 HTTP | 13,100 | 6,895 | 22,310 |
| API02 初始 `SUP-9bb02f7be600485aaedc` | HTTP 500 | 1,358 | 6,486 | 8,523 |

三份 body 的顶层字段恰好为 `model`、`messages`、`max_tokens`、`response_format`。`model="gpt-5.6-sol"`，`messages` 是 system/user 两条消息且 content 均为字符串，`max_tokens=1800`，`response_format={"type":"json_object"}`。当前 `goal_plan` 走 `/chat/completions`；未在这些 body 中加入 tools、stream、temperature、top_p 或 reasoning 参数。API01 的修复请求使用修复阶段 system prompt，user 内容增加 active plan、latest audit 和 recent action facts；初始与修复的区别属于同一生产协议的阶段内容。

原 trace 的 `input_envelope="chat_messages_v1"` 只是包装标记，不是完整请求；`input_chars` 与 `input_sha256` 只记录 user payload，不包含 system prompt 或整个 HTTP body。此次通过原 `GoalPlanRequest.to_dict()`、`rolling_goal_plan()`、`_recent_action_facts()`、公开 workspace metadata 和 `_render_user_payload()` 重建，三个 user payload 的 SHA-256 与字符数均精确匹配原 trace。

System prompt 由冻结 `plan_goal_patch()` 在离线截获点产生，外层 body 由原 `_wire_request()` 产生。因此可以恢复其内容与字段，但原 trace 没有独立保存 system/body 的 wire SHA；报告中的 body 字节数是当前相同 Requests 序列化方式的离线结果，不冒称网络抓包。真实凭据、Authorization 和其他私有 headers 未恢复、未保存。

完整结构化记录见同目录 `REPORT.json`，SHA-256 为 `5d2cee68a91e831fefa289df846cd0efc60785ab133b92857cd2770535076efc`。三个以原 call ID 命名的 `*.reconstructed_body.json` 保存离线恢复结果，其各自 SHA、原 audit SHA、生产源码 SHA 和诊断脚本 SHA 均在该 JSON 登记。这里只新增诊断证据，不据此重试、改路由、调整输出预算或改变双零实验口径。
