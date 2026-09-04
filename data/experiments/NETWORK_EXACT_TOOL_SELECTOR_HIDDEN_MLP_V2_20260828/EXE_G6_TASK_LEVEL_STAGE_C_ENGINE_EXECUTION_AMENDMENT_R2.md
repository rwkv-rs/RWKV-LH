# EXE-G6 task-level Stage C 引擎执行冻结补充 R2

登记时间：2026-08-30；登记时没有启动任何备用 Executor 服务或发起模型推理。

第一次 preparation 在复制隔离引擎后、推理前的测试命令处失败：目标 vLLM Python 3.12
环境没有 `pytest`，而冻结的上游整文件测试还导入了 pinned engine revision 中不存在的、与
state-profile 无关的符号。失败尝试已完整归档为
`invalid_generated_artifacts/run_exe_g6_task_level_stage_c_preparation_missing_remote_pytest_20260830`；
其中 `inference_calls=0`、`experimental_service_started=false`、RWKV raw 未生成。远端副本只改名
保留，没有删除。

不安装或修改远端推理 Python 环境。R2 从冻结测试文件中独立复现 state-profile 相关行为，仍以
原测试文件 SHA-256 `209d5e794b6114a3d7b0074be19dd74027d6de8a113eae8471b19f0203c9f10d`
和 overlay `rwkv.py` SHA-256
`5e5fe3a3e9b2f02b1741f71d0f5072a65fb64212ef508f4e510f5cfa5c2b6434` 失败关闭。覆盖：profile
隔离、逐请求加载、未知 ID、错误 digest、缺一半 ID/digest、损坏 state、错误 model identity、
未固定 manifest、非 zero 默认、缺显式请求 pair、显式 zero，以及本地模型文件 revision。

R2 冻结身份：

- standalone validator：`temp/validate_remote_vllm_rwkv_profiles_without_pytest_20260830.py`，
  SHA-256 `3325521ee0db76fe97cb1ab39a77ef41b837eedcf4649e19efef912330941f9a`；
- preparation：`temp/prepare_exe_g6_task_level_stage_c_remote_20260830.py`，
  SHA-256 `cebdbe7206ae1e72da448f2ce153fdd45a2228c022fe3593f6e0b6808cf9c9b8`；
- engine runner：`temp/run_exe_g6_task_level_stage_c_engine_ablation_20260830.py`，
  SHA-256 `3fd57538d0044b872470d24f82843cac2ba26d20f264dafeaf7429a1835edba5`。

原预登记的引擎、交替顺序、raw equality、延迟、GPU0、产品 18070、零 stage switch 和所有质量
门槛不变。只有测试执行载体从缺失的 pytest CLI 改成相同断言的 standalone validator。
