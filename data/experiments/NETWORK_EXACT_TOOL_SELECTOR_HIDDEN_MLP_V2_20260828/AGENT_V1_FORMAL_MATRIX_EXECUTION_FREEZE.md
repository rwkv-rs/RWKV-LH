# Agent V1 第一正式简体版执行冻结

登记时间：2026-08-30；登记时 G9 仍在 GPU0 训练，Stage C 和 Agent V1 尚未产生任何
G9 推理结果。

## 固定输入

- 能力矩阵预登记 SHA-256：
  `d54fdfd9abe0282259222df732980dd9fb60fb22670e4bb98133b57706d9cdb2`；
- WEB01 manifest/tasks/hidden acceptance SHA-256：
  `c42ab96bd34bfd8b3150250b54e2dab31bda2aa483ef69ad6851483832a172a2`、
  `87f54fabcf2584ebc74840559e4abb86b31e5e9744c4037d052c318e884c176f`、
  `0fae91dfd7ed78afc0139ba4fea6f0566d1288d33acfb62097ed88d1d6f6a19f`；
- NET01 cases/manifest SHA-256：
  `dbd67f33bbd4abbb4a38d95ec611977b615061687897e1597dc04ffbf56b22e7`、
  `7204fc8aebfecea0995606b48115219e237e14f72714e4e98bb45ba1be43be61`；
- E2E runner/request-delivery validator/NET01 runner SHA-256：
  `d45ed6bb3aa08578b60661de662838cadb690c51cab6cdc36dd4ff4815009c80`、
  `2a96c53cfe66ec27d6c43f985292e800a0350308f5cce032cc5fa5e112a46bb0`、
  `60832921cdec5cacc5c9ae9a344bac317cef1a309bb094d6f08abfd95582a970`；
- formal matrix runner：`temp/run_agent_v1_formal_matrix_20260830.py`，SHA-256
  `30ee41d5928f19c59357b4e44786cb867804402f935032c71ee6a4f1e837154d`。

## 固定执行

只有 Stage C2 已按最少 state 规则选择一个部署臂，才允许执行。本实验单次启动隔离
multi-profile Executor 与 S60，保留产品 18070：

1. `A_GENERAL_G3` 运行 WEB01；
2. Stage C 选中部署臂以同一 strong Planner + S60 + Harness 运行 WEB01；
3. 九个既有 case 的 control/candidate 指标直接读取 Stage C Full90 的 immutable per-case
   结果，保持预登记顺序，不选择性重跑；
4. 选中部署臂运行 NET01：公开检索 → grounded JSON → 创建本地 verifier → Harness 内运行
   verifier → 再读取 artifact → byte-exact RWKV final；
5. 所有 Executor 请求必须使用显式 request profile，Selector/Executor task 内 switch=0，
   Planner 为 `contract_graph` 且 Harness authority=false。

WEB01 使用 concurrency=1、max transitions=200；NET01 使用 max transitions=200。任何业务失败
不得隐藏重试。provider transport retry 只沿用 `.env` 已冻结的公开配置。

## 固定门槛

- candidate WEB01 strict/external/completed 全部通过且 integrity valid；
- 既有九例 external `>=8/9`、completed `>=8/9`，M02/H07/LH12 强制通过；
- 相对 G3，strict/external 净增益非负且 control strict-pass 零回归；
- NET01 1/1，通过全部 grounded fields、local verifier 时序和 profile-stability 检查；
- raw modification/deletion/reorder/hide=0，Planner tool authority=0，scope violation=0，
  产品 18070 全程保留。

任一门槛失败，结果必须为 `not_ready`。失败 case 只用于后续全局 state-tuning 数据构建，
不得修改验收、增加用例特判、降低阈值或用 Controller/Parser 替代 RWKV 能力。
