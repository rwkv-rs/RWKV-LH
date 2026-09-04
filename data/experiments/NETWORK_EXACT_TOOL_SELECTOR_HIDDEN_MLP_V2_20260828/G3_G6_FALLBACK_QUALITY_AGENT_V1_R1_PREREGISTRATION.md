# G3/G6 task-level 双 state 联网质量与 Agent V1 R1 预注册

登记时间：2026-08-30（Asia/Shanghai）。本文件在本轮任何 RWKV/Planner 请求前冻结。

## 已满足的进入条件

- G9 八 checkpoint 结果为 `no_candidate_passed`，因此按
  `EXE_G6_TASK_LEVEL_MULTI_PROFILE_FALLBACK_PREREGISTRATION.md`（SHA-256
  `9b5956a70fa103256ca6cb880f64352aa7a57a0d2f1c0e2f6dfa5c845708a34e`）触发备用架构；
- deterministic CMix R7 的只读 R2 裁决 SHA-256 为
  `72bc522c390a9033a4e6c47145d50bed7de7f38e38e09b290803491be311293e`，状态为通过且允许质量消融；
- profile preparation SHA-256 为
  `88fb9c7e3754b5807dcae35f6255e5011007629b128e3a6ee36a31e0e4711d0b`；
- post-R7 retrieval9 结果 SHA-256 为
  `30e9422840e42f4df103e6a096bcd36ac9cfe21743e6a0a7f3767d332f881f45`，9/9 hard gates。

## 固定架构与身份

- Selector：2.9B S60，zero state，Hidden(mean+last)+h64 MLP，只看 25 个名称/一句描述；
- Planner/Reviewer：`.env` 当前 strong model，Harness authority=false；
- Executor：同一 13.3B base，同一 deterministic CMix candidate extension，在任务创建时一次性绑定：
  - offline/general：`EXE-G3-MULTISTAGE-STEP2000`，state SHA-256
    `13f6586951666962405286dda8e45c1eae82a37c68c21b3b75dbbb04c6e54f12`；
  - 非 offline/network：`EXE-G6-NETWORK-RECOVERY-STEP1500`，state SHA-256
    `611d9e5564ef47413c1bd1536500e987270c8303b2c87d5d54bca256d57dd68b`。
- task 内 main/atom 不切换 state；不根据关键词、operation、阶段或结果路由；不在联网后切回 G3。
- physical remote GPU0 UUID：`GPU-1faf7f09-25f4-2515-b707-6e0766aa841d`；产品 18070 不重启。

引擎 launcher SHA-256：
`cde2daffdc4e71c9aa490eaecd8cf035475147fb94c718f80262ab9d5bb1b8be`；candidate extension SHA-256：
`31b64460dca6bc9d6b73a17120137822ae8b740eb5f3a3ee1fffbb1ea4a00fb1`。

## 固定执行顺序

在一次隔离 multi-profile 服务和一次 S60 服务生命周期内，固定顺序运行：

1. `A_GENERAL_G3_FULL90`：冻结 90 例、G3、strong Planner、concurrency4、max transitions200；
2. 对同一 90 个 immutable RunState 以生产 resolver 证明 `D_DUAL_G3_G6` 的 offline 绑定逐例仍是
   G3；不重复生成第二份随机 Full90；
3. D/G6 完整运行 live V1 2 例、grounded V2 6 例；
4. G3 control WEB01 一次，D/offline WEB01 一次，均 concurrency1、max transitions200；
5. D/G6 运行 NET01：公开检索→grounded artifact→本地 verifier→复读→RWKV final；
6. retrieval9 直接引用本轮已经按独立预注册完成的 immutable 9/9 结果，不重复消费 provider；
7. 九个旧能力 case 从 A Full90 immutable per-case 结果提取，顺序固定为 B10、M02、M09、H01、
   H07、H10、LH01、LH10、LH12，不选择性重跑。

固定实现 SHA-256：Full90 runner
`d45ed6bb3aa08578b60661de662838cadb690c51cab6cdc36dd4ff4815009c80`；request-profile validator
`2a96c53cfe66ec27d6c43f985292e800a0350308f5cce032cc5fa5e112a46bb0`；live wrapper
`03a10423a2d70b601595a47a4f16f443c2e1e9fdc30ca563a9cc6390a3a29ee0`；NET01 runner
`60832921cdec5cacc5c9ae9a344bac317cef1a309bb094d6f08abfd95582a970`；S60/factor helper
`37efc77df3c3113f9aefcbcf728a5efe5b512568f4910b86f38f43f8693c78aa`。

## 固定门槛

1. Full90 调度 90/90、完整性 valid、request profile、generation input=raw generation、Planner tool
   event=0、RWKV raw modification/deletion/reorder/hide=0；唯一允许的 capability boundary 是冻结
   `E2E-LH09/mock_api`，但仍必须留痕；
2. D 的 90 个 offline routing 全部解析为 G3 且 task 内 profile switch=0；
3. live V1=2/2、V2=6/6、grounded fields 全匹配；retrieval=9/9；
4. candidate WEB01 strict/external/completed、公开 verifier 和 integrity 全通过；control 只作对照；
5. 九例 external `>=8/9`、completed `>=8/9`，M02/H07/LH12 必过；
6. NET01=1/1，检索 evidence、artifact、verifier 时序、复读、final 和 profile-stability 全通过；
7. Selector/Executor task 内 switch=0，Planner 工具执行权限与事件=0，scope violation=0，acceptance
   leakage=0，hidden retry=0，postprocess=false；产品 18070 全程健康；
8. 所有 RWKV response/raw token/finish 先追加保存，Parser/Harness 不修改、删除、隐藏或重排。

全门槛通过才标记 `ready`。任一失败标记 `not_ready`，并按完整失败簇构建下一轮约 2000 条旧 Agent
能力 state-tuning 数据；不得降低门槛、重跑有利个例、加入 benchmark 特判或让强 Planner/Controller
替代 RWKV 执行。
