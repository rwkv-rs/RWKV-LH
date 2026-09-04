# EXE-G9 Stage C1 多 profile 引擎执行冻结

冻结时间：2026-08-30；G9 仍在 GPU0 训练，尚未产生 G9 推理结果，本文登记后不得为改善结果修改口径。

## 固定输入与程序

- 上位预登记：`EXE_G9_STAGE_C_MINIMAL_STATE_ENGINE_PREREGISTRATION.md`，SHA-256
  `5e5105dbfac93ec6277d3d881b19421215385cac7859137747d4969716f9d9b8`。
- 隔离引擎准备器：`temp/prepare_exe_g9_stage_c_remote_20260830.py`，SHA-256
  `a43a9c12c92115253103e0c9bc249ee6441722255e461248af7b761c41170420`。
- recovery72 raw-first evaluator：
  `temp/evaluate_executor_multi_profile_recovery72_20260830.py`，SHA-256
  `f7c88bba16389d4cced71601c952cd0a09b6ec741b5a869c204e0fcd0c20f083`。
- Stage C1 runner：`temp/run_exe_g9_stage_c_engine_ablation_20260830.py`，SHA-256
  `739df0e1f9743e79da73e9f8a147c3cbf0893a6253cceefae2a27f4d30c2ae96`。
- 隔离 overlay：`envs.py` =
  `dcfe3da9cfd7e7b3c8c0afa8315987987fd43af787210474b102ad8621be2f1a`，
  `rwkv.py` = `5e5fe3a3e9b2f02b1741f71d0f5072a65fb64212ef508f4e510f5cfa5c2b6434`，
  `test_rwkv7.py` =
  `209d5e794b6114a3d7b0074be19dd74027d6de8a113eae8471b19f0203c9f10d`；
  准备器和 runner 常量逐文件强校验。

## 固定执行顺序

只有 G9 八臂消融选中、Stage B 全通过、准备器全通过时才运行：

1. 在物理 GPU0 独立启动 G3，按源文件顺序、并发 1 运行 recovery72。
2. 独立启动胜出 G9，以完全相同 prompt、采样和顺序运行 recovery72。
3. 启动隔离多 profile 引擎；显式 zero pair 做一次 raw-first 成功探针。
4. 对每个 recovery sample 依次请求 `G3→G9`，再在独立完整轮次请求
   `G9→G3`；每个请求仅一次，禁止隐藏重试、输出修复或后处理。
5. 停止 18075 后才比较 dedicated 与两种交替顺序；18070 全程保留。

每个请求固定 temperature=0.1、top-p=1、top-k=0、seed=1067、max tokens=256；
完整 response body、text、token IDs、finish reason、profile ID/SHA 和请求体均先
append+fsync，再解析。比较 raw text、token IDs、finish reason 与 canonical pass/fail，
每个 profile 必须 72/72 三方完全相同。

## 固定延迟与门槛

startup 不计入 warm latency。每个 dedicated/profile 只排除该 profile 的第一个请求，
其余 71 个请求固定进入 p50/p95；所有被排除请求仍保留在 raw journal。多 profile 相对
对应 dedicated 的 p50 必须 `<=1.25x`，p95 必须 `<=1.35x`。

缺 pair、半 pair、未知 ID、错误 request digest、损坏 state、错误 model artifact/revision
必须在 recurrent row 分配前失败；显式 zero/G3/G9 必须成功。task-level general/network
binding、resume 防切换、main/atom 同 identity 使用冻结测试执行。任一门槛失败，Stage C2
不得选择或激活任何 G9 配置。
