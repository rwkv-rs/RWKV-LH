# CLI 与数据项目开发题

来源：owner-authorized authored development benchmark。四题为人工编写的开发基准，不是生产 trace，不得直接当成角色 StateTune 样本。

每个任务目录的 `task.json` 是唯一 Agent 可见材料来源；仅其 `workspace_files` 与 `workspace_generators` 可投放到 Agent workspace。`reference/`、`private_verify.py`、`mutation.json`、作者验证工件和 manifest 均不得进入 Agent workspace。私有验收使用固定 seed 自行生成输入，通过真实 CLI 与文件结果验证，不读取其他题集、acceptance、Holdout 或 confirmation。

私有验收入口：`python private_verify.py WORKSPACE`。成功退出 0；失败退出非 0。仅依赖 Python 标准库。
