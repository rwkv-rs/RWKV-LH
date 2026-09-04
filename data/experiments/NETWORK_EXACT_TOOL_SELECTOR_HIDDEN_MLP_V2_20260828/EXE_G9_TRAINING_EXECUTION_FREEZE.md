# EXE-G9 远端训练执行冻结

冻结时间：2026-08-30；在 G9 训练进程启动之前。

- 数据冻结：`EXE_G9_DATA_FREEZE.md`，SHA-256
  `5245742acc90bdd0f0e1db2f287d162706b0b49eeb323b1486d79025b3552127`；
- 训练前 manifest：`run_exe_g9_state_training_remote_preflight/EXE_G9_RUN_MANIFEST.pretrain.json`，
  SHA-256 `a7730b4b3bffd8e2bd082be17202178050ec766aa69fd3152ee03fc7c8f7d604`；
- 训练数据权威 loader 报告 SHA-256：
  `313339502a22f2e4bbf9794566b221eade15d4afb1dfe8f295f0e24f4fdee7a9`；
- 训练/服务 tokenizer 对齐报告 SHA-256：
  `7848235ac4f15b4e9649d3b39610e1553c0bf57a9c7e31d5b3f8ce0997ce2476`；
- 远端 launcher：`temp/run_remote_exe_g9_stable_schema_contrast_state_tuning_20260830.sh`，
  SHA-256 `8f43371a3c2e308d9f0bf6e32230b1eeaab6dec18953324aa9e604777c34c9d2`；
- preflight recorder SHA-256：
  `64b4ed5731cf08b7e04813500198226667d0dbf274dc42df2878b4e18286eccb`；
- authoritative loader validator SHA-256：
  `dd6929187e1350f7a6b49f83e91108621e557b46340074e9801b93300a0219de`；
- tokenizer alignment validator SHA-256：
  `9cd607fadae29d6a326d072eeeb1a7af7ab8e32927f77fc2601e80bbdd450cf1`。

预检事实：physical GPU0 UUID 为
`GPU-1faf7f09-25f4-2515-b707-6e0766aa841d`，空闲 `58084 MiB`；产品 18070
监听且健康，实验端口 18075 空闲，无其他 `train.py` 进程，G9 输出目录启动前不存在。

训练固定为：G6 step1500 parent、单 state continuation、BF16/FLA、ctx2496、2000 step、
每 250 保存、cosine LR `5e-7 -> 5e-8`、warmup40、seed1091、`CUDA_VISIBLE_DEVICES=0`。
进程必须自然结束；不得 early-stop、删除或覆盖 checkpoint，也不得停止 18070。
