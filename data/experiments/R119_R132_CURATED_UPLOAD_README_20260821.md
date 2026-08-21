# R119–R132 curated server upload

日期：2026-08-21  
用途：把 R119–R132 架构实验中可复核、可复用且体积合理的证据上传到 GitHub `origin`，
作为研究数据记录；**不是**把 R129–R132 的 REVERT 机制发布成新最佳架构。

## 入选口径

1. 固定数据与评价口径的 preregistered protocol、source manifest 和程序级结论。
2. 每个关键 Full90 的 round-level `results.json`、`REPORT.md`、`RUN_PROTOCOL.json`、
   `runtime_doctor.json`、`source_tree_manifest.json` 与人工因果分析。
3. R123 invalid fixed-point、R130 canonical repair、R131 invalid→repaired 和 R132 terminal
   negative result，因为这些记录包含可迁移的根因与回归边界。
4. R124–R126 本地归档目录只有 round-level 报告/分析时，保留这些已登记结论；不强行上传
   `.gitignore` 下的重复 `outputs/` 副本。
5. R130/R132 的 WSL 资源与 continuation amendments，因为它们解释了 per-case worker 回收、
   concurrency 1 和有效 Full90 的运行边界。

## 明确排除

- 所有 `cases/`、workspace、逐题 SQLite/WAL、模型状态和重复 raw trace；这些本地目录合计约
  95 GB，主要是可由已冻结源码/参数重新生成的运行状态。
- R130 的多次资源崩溃/传输超时目录；只上传修正协议和最终有效轮的 round-level 证据。
- `temp/`、`.venv/`、`outputs/` 与测试临时目录。
- R129/R130/R131 被 REVERT 的 active source diff；上传的是否证数据，不把失败机制部署为
  generic 默认路径。
- 与 R119–R132 结案无关的用户本地修改。

## 数据来源、版本和生成

- 数据集：`data/datasets/rwkv_e2e_90_v1/manifest.json`，版本 `rwkv-e2e-90.v1`，90 题；
  visible tasks、hidden acceptance 和 Codex reference 的 SHA-256 已在该 manifest 中冻结。
- 模型与参数：各轮 `RUN_PROTOCOL.json`；R132 最终使用
  `rwkv7-g1i-13.3b-20260805-ctx16384`、temperature 0.05、top-p 1、top-k 0、
  max-transitions 200、concurrency 1、transport `prompt_replay`。
- 评分：每轮固定 `results.json` 与 preregistered gate，不作运行后口径调整。
- 上传文件的相对路径、字节数与 SHA-256 由
  `/home/chase/GitHub/RWKV-LH/temp/generate_r119_r132_curated_upload_manifest_20260821.py`
  机械生成到同级 `R119_R132_CURATED_UPLOAD_MANIFEST_20260821.json`。

## 结论边界

- 终局结果：R132 34 TP / 30 FP / 0 FN / 26 OTHER，REVERT；不运行确认轮。
- 最佳有效基线：R126 official 36/30/0/24，远端分支
  `baseline/round126-v19p1` 已存在于 commit `50754a2cc1d4b4fcf44d2a93f3888cd070a9c962`。
- 本上传只新增研究证据提交，不改写该最佳基线、不上传 REVERT 源码、不 push `main`。
