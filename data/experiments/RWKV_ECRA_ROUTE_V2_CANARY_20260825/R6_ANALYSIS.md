# r6 canary analysis

r6 保持 r5 固定指标口径，完整运行 7 例，仍未通过：network macro-F1
0.2222、web/connector macro-F1 0、required-online FN 1.0、privacy backend
execution 0、Strong Planner concrete operation count 0。

r6 已排除“网络工具不可见”根因。所有 v2 read-only work atom 的菜单均含本地、
网页、连接器和确定性能力；但 RWKV 对网页、GitHub、PyPI 和隐私 case 从未选择
网络工具。trace 显示：

- 天气 atom 执行 `list_directory` 后，RWKV 的候选文本准确指出应使用
  `web_search` 或 `connector_lookup`；
- GitHub atom 执行 `list_directory` 后无证据声称默认分支为 `main`；
- PyPI 的第二个 public atom 再次读取 `pyproject.toml`，并表示环境不允许外部调用；
- `.env` atom 选择目录列表后声称 `read_file` 不在 contract，实际 allowset 中存在；
- progressive menu 被 `LongHorizonModel` 全局重排为 `list_directory` 首位，
  `ScopedAtomHarness` 同时丢弃 capability projection 的有序结果。

因此根因是有序能力投影在 Worker 边界被覆盖，加上 G1i selector 的首项偏置，
不是 Planner 具体工具下发，也不是网络策略拒绝。

r7 机械保留所有候选，只使用 Planner 已获准输出的抽象 evidence-source class
作为软排序：`workspace_file / workspace_directory / deterministic_compute /
public_web / structured_registry`。Strong Planner 不能写操作名；Controller 不会
因提示删除任何工具；Scoped Harness 和 Model 必须保留投影顺序。新 v2 finalizer
以 max-actions=0 直接进入 Final，旧 v1/v4 trace 保留历史行为。
