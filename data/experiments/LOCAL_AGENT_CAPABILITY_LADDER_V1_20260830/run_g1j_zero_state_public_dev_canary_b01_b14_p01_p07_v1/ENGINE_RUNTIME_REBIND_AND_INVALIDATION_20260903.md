# Executor 工程内重绑定与失效运行记录

日期：2026-09-03（Asia/Shanghai）

## 根因

首次 B01、B02 和未完成 B04 的 Executor 服务使用了工程外可执行文件 `/home/chase/.venv-vllm-rwkv-8e90d04ecb/bin/vllm` 与工程外源码。这违反固定项目运行时身份，因此这些轨迹不能用于 zero-State 能力统计。

工程内引擎初次接管时又暴露了两个独立的启动缺陷：

1. 迁移器将三个仅用于无损来源保留的 layer-zero value-mix 张量写为模型根目录的第二个 `.safetensors`，默认加载器将其误识别为运行时分片。
2. 工程内隔离 `.venv` 缺少当前 vLLM `requirements/common.txt` 已声明、API 路由会无条件导入的 `model-hosting-container-standards`。

## 系统性整改

- 原生 State API 补丁已经并入 `data/runtime/engines/vllm-rwkv-67f0c5996c50`，不再依赖工程外源码。
- 迁移器把非运行时张量放到 `source_preservation/native_unused_layer0_value_mix.safetensors`；模型根目录只含 `model.safetensors`。
- 新旧保留文件中的三个张量已逐键检查 dtype、shape 和值，结果 bitwise equal。
- 主运行时 `model.safetensors` SHA-256 仍为 `a5b4fbab12ce321f57ba0e9a00ddf32e5b3644f8b50216cc6ef14aba841efefd`，表明运行权重未变化。
- 工程内 `.venv` 从本机离线缓存补齐固定 `model-hosting-container-standards==0.1.16` 及其缺失依赖；没有训练、量化或推理参数改动。

## 当前冻结身份

- 引擎路径：`/home/chase/GitHub/RWKV-LH/data/runtime/engines/vllm-rwkv-67f0c5996c50`
- 引擎版本：`0.23.1rc1.dev1942+g67f0c5996`
- 模型制品路径：`/home/chase/GitHub/RWKV-LH/data/models/rwkv7-g1j-13.3b-vllm-v1`
- 制品 manifest SHA-256：`4eff9f7054e52d702c43132855e943a8fce3269e578a0160752363775b3d6647`
- 原始 PTH SHA-256：`559371f5b9aef13189ae54b345ac096af4ad2b689996c05d89de687612b3ae65`
- State profile：`zero`，SHA-256 为 64 个 `0`

服务日志已确认只加载一个权重分片（`1/1`），`/v1/capabilities` 报告 `prompt_replay=false` 和完整 `rwkv-lh.native-state.v1` 能力。固定验收记录 `runtime_acceptance/PROJECT_ENGINE_ZERO_STATE_NATIVE_CHAIN_20260903.json` 对 create、append、generate、rollback、commit、export/import 与 fork 全部判为 true，且 `seed_sent=false`。

## 无损归档

- 工程外旧服务运行时：`runtime/engineering_invalid/EXECUTOR_ENGINE_OUTSIDE_PROJECT_PRE_REBIND_20260903`
- 原始 PTH 直接入口失败：`runtime/engineering_invalid/PROJECT_ENGINE_RAW_PTH_ENTRY_INVALID_20260903`
- 辅助权重根目录误载失败：`runtime/engineering_invalid/PROJECT_ENGINE_HF_AUXILIARY_ROOT_GLOB_INVALID_20260903`
- 工程内 venv 依赖缺失失败：`runtime/engineering_invalid/PROJECT_ENGINE_VENV_DEPENDENCY_INCOMPLETE_INVALID_20260903`
- 首次 B01/B02/B04：`public_dev/seed_20260903/engineering_invalid/EXECUTOR_ENGINE_OUTSIDE_PROJECT_*`
- 旧的辅助权重根目录制品：服务器 `data/models/engineering_invalid/rwkv7-g1j-13.3b-vllm-v1_auxiliary-root-glob_20260903`

以上均为移动归档，没有删除原始日志、State、数据库、轨迹或工作区。
