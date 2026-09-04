# REAL_HARNESS_V2 — INVALID PRE-MODEL

- 状态：无效，不进入任何指标。
- Planner/Selector/Executor 模型调用：0。
- 实验服务启动：0；产品服务未受影响。
- 冻结文件 SHA256：`93f538cb9e5103e3ae50dc75ed45c3866fb5d58e435b53a3c51d152a8729b21d`。
- runner SHA256：`686bca272c7a3e799075aafef31edaf5bfd81742a1a808ed0e08d73cb9edce77`。
- 原因：wrapper 错误地从外层 engine 读取只存在于内层 base runner 的 `REMOTE_PROFILE_ROOT`，在任何 preflight 或外部调用前触发 `AttributeError`。
- 处理：保留本记录；删除该无效属性赋值，以新的 V3 freeze/tag/output 运行，不覆盖 V2。
