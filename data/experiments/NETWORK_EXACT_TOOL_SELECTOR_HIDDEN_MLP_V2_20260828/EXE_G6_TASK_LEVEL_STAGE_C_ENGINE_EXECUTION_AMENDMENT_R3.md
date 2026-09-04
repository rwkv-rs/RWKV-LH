# EXE-G6 task-level Stage C 引擎执行冻结补充 R3

登记时间：2026-08-30；R2 engine runner 在本地创建输出目录、启动远端 18075 或发起模型请求
之前，于 launcher identity preflight 失败。产品 18070 健康、18075 空闲、推理调用数为 0。

根因仅为远端 G6 dedicated launcher 的冻结路径写错：实际已验证文件为
`/home/chase/chase/RWKV-PEFT/temp/run_remote_exe_g6_network_recovery_candidate_vllm.sh`，
SHA-256 仍为
`3d6f0841959e4929e178c3cf42ecabb66ea38558f6919d4785999e3c3d13c69a`；错误路径
`.../scripts/...` 不存在。

只修正该路径后的 engine runner SHA-256 为
`731b0acc1a32c84ef9dbab3d32e8fb847555ec4db29c2681bb27b51ec1bba5f4`。其余源码、数据、
profile、顺序、门槛和 R2 validator 身份全部不变。
