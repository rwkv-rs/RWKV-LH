# INVALID — pre-API runner defect

- 状态：无效，不进入任何指标。
- API 调用数：0。
- 原始 runner SHA256：`c0608c68ec0daaf4c3b96868c76ee3fbdc2861b70c8317b7c9934ebfb5ba1960`。
- 错误：runner 从 `PATCH.json` 读取不存在的 `request_digest`，在第一个 HTTP 请求前触发 `KeyError`。
- 处理：保留本目录；修正值改从已保存的初始 `REQUEST.json` 精确读取，并以 V2 新目录运行，不覆盖本记录。
