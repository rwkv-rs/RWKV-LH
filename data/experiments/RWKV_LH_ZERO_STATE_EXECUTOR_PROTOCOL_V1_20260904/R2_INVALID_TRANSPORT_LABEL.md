# R2 评价器无效

R2 四条 decision 均为 `accepted: true`，并记录 `transport: native_rwkv`；但测试脚本错误地把通过条件写成不存在的字符串 `native_rwkv_state`，因此产生 `passed_count: 0` 的机械假阴性。

实现中的 `NativeModelSession.transport` 固定为 `native_rwkv`（`rwkv_lh/model_session.py`）。R2 原始文件 `R2_RESULT.json` 保留，不覆盖。该无效原因与模型输出内容无关。
