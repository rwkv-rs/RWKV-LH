# G1J 与 G1I 当前角色能力配对审计

日期：2026-09-01。性质：对既有冻结结果的事后配对审计，不冒充预注册新实验。

## 结论

在唯一可严格逐样本对齐的 2.9B Selector S60/V7 开发集上，G1J 修复了 G1I 的 10 条错误，
但新增 29 条回归，另有 29 条两代都错误。G1J 总错误从 39 增至 58，整体 accuracy 从
`2532/2571 = 98.4831%` 降至 `2513/2571 = 97.7441%`，净变化 `-0.7390` 个百分点。

这不是 JSON、`PlanPatch`、HTTP 或解析失败。2571 对样本的 label、source sample、split、kind、
language 和 position 全部一致；两侧都有完整 logits，`selected = raw_argmax`，且
`postprocessed=false`。差异对象是 2.9B Selector 的工具分类字段 `selected`。

本比较也不能回答“G1J 裸模型是否比 G1I 裸模型强”：两侧使用同一 S60/V7 数据和 h64 Head
配方，但 Head 分别在各自基座 Hidden 上重新训练。本结果比较的是“基座 + 匹配 Head”系统。
用户观察到的 G1J 未训练初始准确率更高，与本结果不冲突。

## 冻结证据

- 数据：S60/V7 dev，共 2571 条；同一 sample identity 集合。
- G1I predictions SHA-256：`dee6311c9bfbc94a89421361745fa094eb2ac33da76c5338a82a5b41ce53b312`。
- G1J predictions SHA-256：`15b9fab5fe27603afc1e7e68e607bbf5c68d9174149f2d9dc2bd73a497594d39`。
- G1I：2.9B G1I、zero State、S60/V7、匹配 h64 Head。
- G1J：2.9B G1J、zero State、S60/V7、匹配 h64 Head。
- locked test：G1J 因 S39 dev gate 失败没有打开，不能比较。

## 分片结果

| slice | 样本 | G1I correct | G1J correct | 净变化 | G1I accuracy | G1J accuracy |
|---|---:|---:|---:|---:|---:|---:|
| S28 | 750 | 749 | 750 | +1 | 0.998667 | 1.000000 |
| S39 | 857 | 831 | 815 | -16 | 0.969662 | 0.950992 |
| S52 | 399 | 390 | 389 | -1 | 0.977444 | 0.974937 |
| S53 | 325 | 324 | 320 | -4 | 0.996923 | 0.984615 |
| S55 | 240 | 238 | 239 | +1 | 0.991667 | 0.995833 |
| 全部 | 2571 | 2532 | 2513 | **-19** | **0.984831** | **0.977441** |

S39 是唯一跌破预注册门的分片：G1J accuracy `0.950992`、macro-F1 `0.949275`，门槛均为
`>=0.96`。G1I 对应值为 `0.969662/0.967452`。配对类别为：both correct 2503、G1J 修复
10、G1J 回归 29、both wrong 29。英文为修复 7/回归 21；中文为修复 3/回归 8。

## G1J 修复的 10 条

表中 `G1I -> G1J` 的右侧就是固定 label。

| slice | sample | lang/kind/pos | label | G1I -> G1J |
|---|---|---|---|---|
| S28 | `S60-54dab554413d95bc4b42032e` | en/independent-prefix/2 | check_command | run_command -> check_command |
| S39 | `S60-20fc5fc870d1ad78fe927106` | zh/history/1 | read_file | date_diff -> read_file |
| S39 | `S60-533e724d37be369319e81135` | en/current/1 | patch_json | connector_lookup -> patch_json |
| S39 | `S60-5e31813a3363d41298656e88` | en/current/1 | check_command | replace_text -> check_command |
| S39 | `S60-62d3bcff67dffbd36d780be2` | zh/history/1 | read_file | current_time -> read_file |
| S39 | `S60-f54b266851cf44f6a3b0d0dd` | zh/current/1 | write_json | list_directory -> write_json |
| S39 | `S60-fc384f8a7e9ea68cc99f6425` | en/history/1 | read_file | file_digest -> read_file |
| S52 | `S60-b35543f7342b66d408adf7ad` | en/history/2 | read_file | write_json -> read_file |
| S55 | `S60-0ea1f3ab2cb9531f8a19b420` | en/history/2 | write_json | read_file -> write_json |
| S55 | `S60-8867af40e8c27a43fcb0194b` | en/history/2 | write_json | read_file -> write_json |

## G1J 新增回归的 29 条

| slice | sample | lang/kind/pos | label | G1I -> G1J |
|---|---|---|---|---|
| S39 | `S60-10c5f52faf65e25fa6c4f124` | en/current/1 | list_directory | list_directory -> read_file |
| S39 | `S60-1577792056c2e6e8e17d261c` | en/history/1 | make_directory | make_directory -> append_file |
| S39 | `S60-17124ceb8164ee82f760425a` | zh/history/0 | read_file | read_file -> search_text |
| S39 | `S60-20ddfbe18f8fce587b270178` | en/current/1 | current_time | current_time -> connector_lookup |
| S39 | `S60-3eeda6a5b8188ea1135bd746` | en/current/0 | file_digest | file_digest -> move_file |
| S39 | `S60-4877dd2cefe329c0353a7f83` | en/history/0 | search_text | search_text -> replace_text |
| S39 | `S60-4a41a6461b2116279cc1b55c` | en/current/0 | append_file | append_file -> read_file |
| S39 | `S60-4d643160ab69200133dac645` | zh/current/1 | final_answer | final_answer -> calculator |
| S39 | `S60-519ea7d252f8be0cb46ab13e` | en/history/1 | bind_evidence | bind_evidence -> read_file |
| S39 | `S60-55bf04ada5747dc8d0a19579` | zh/history/0 | read_json | read_json -> patch_json |
| S39 | `S60-6f5c673492b569a6c57ff331` | zh/history/0 | list_directory | list_directory -> search_text |
| S39 | `S60-8ab32a63904e683ce18b479f` | en/current/0 | check_command | check_command -> read_file |
| S39 | `S60-93092bf2248a1c70533664d0` | en/history/1 | search_text | search_text -> read_file |
| S39 | `S60-96231e645f8a147c4ddc751c` | zh/history/1 | file_digest | file_digest -> copy_file |
| S39 | `S60-96cebe973329bbb2e76fb326` | en/current/0 | write_json | write_json -> write_file |
| S39 | `S60-b1a15f0078e1b29fc80378de` | zh/history/1 | make_directory | make_directory -> append_file |
| S39 | `S60-b6095e7e3db9881baa203f05` | en/current/0 | remove_line | remove_line -> read_file |
| S39 | `S60-c8b29d2643200dfb7fb12224` | en/history/1 | file_digest | file_digest -> read_file |
| S39 | `S60-d3aa235d78d5200244b7bd06` | en/history/1 | make_directory | make_directory -> append_file |
| S39 | `S60-e26b2c759065f280de391931` | en/history/1 | read_json | read_json -> read_file |
| S39 | `S60-f143c0de82ae8c7de2b7eab6` | en/current/0 | write_json | write_json -> write_file |
| S39 | `S60-fa808250b87e9b2c0aa7cad1` | zh/current/1 | check_command | check_command -> run_command |
| S52 | `S60-199019749a5c5e0f8a4bdc76` | en/history/1 | write_json | write_json -> patch_json |
| S52 | `S60-750b57ad38a27a54d21efdf1` | en/history/4 | final_answer | final_answer -> check_command |
| S53 | `S60-58a76497ad1d113902df3a49` | en/history/2 | read_file | read_file -> write_file |
| S53 | `S60-b5863577d98b1fb23c62a857` | zh/history/3 | read_file | read_file -> write_json |
| S53 | `S60-d2dbed39edf7e0858d2e91bb` | en/history/3 | read_file | read_file -> write_json |
| S53 | `S60-e1b9bf6b0c518c3392996c0a` | en/history/3 | read_file | read_file -> write_json |
| S55 | `S60-45b28cd0ab636876e8649716` | en/history/1 | read_json | read_json -> calculator |

## 两代共同错误的 29 条

这些样本不是 G1J 新增问题，但说明旧 S60/V7 输入职责本身仍有稳定残差：

```text
S39: S60-04e668230d045817d4cda4d7 S60-378cc9bb499e07a42a849e1e
     S60-3ac66f8f98d22528bdd1fd18 S60-4050c984cf5b2cef858b4914
     S60-5854a052efe4e1e36567c852 S60-602750bb9039d324a11e4f2f
     S60-6602de0424876a2e2c00aee6 S60-7f06901c2f2ca48fe0bb8646
     S60-8319c8d54261588036c0c2f8 S60-86665c8e48b8f065959a516f
     S60-94c4978b06a31c73a4d544ce S60-9fab37ea87dee0d6459e397c
     S60-a7f54a58c3f07b626156be5f S60-b2f291d6e562f5401ab4ffcc
     S60-cd604e86900d078372c78139 S60-d3221008bd321f66487bc33a
     S60-e3d4ad5d8d54a47a2933e4e2 S60-fabce6a8212a7debd5d33d93
     S60-feae67b86a7336f7a62a97f3 S60-fef7e854cb5bdbfd7e9012f8
S52: S60-14068547df7e98881ac26757 S60-5b4084c79534db400bc424e3
     S60-63e39f2d39927456297f64bb S60-78052c738408af372700d826
     S60-972a6a6fb1f9cf5164c9d3d5 S60-b90f53ac91597d4f3f4f9dfa
     S60-be9f827e81decfc90b588a26 S60-e397366acb963686103a8694
S53: S60-bdcd4cb3b92944f011697ebc
```

## 13.3B Executor/Auditor 边界

当前 role-pure Prompt、产品 stop suffix、zero State 下，G1J 13.3B 已通过 Executor 参数生成 `1/1`
和 Auditor `2/2`。同一 G1J 13.3B 在旧 correction Prompt 上曾为 `0/3`：首对象有工具意图错误，
Audit 首对象也不是 `audit_decision`。这直接证明 Prompt/职责边界能主导结果，不能把旧 `0/3`
当成新架构下的模型缺陷。

没有一份 G1I 13.3B 在当前 role-pure Prompt、zero State、相同 stop suffix 上的配对 raw trace。
历史 G1I Agent Ladder `0/3` 同时混入 G3/G6 State、旧 Contract Graph、错误 Selector 输入和旧 Audit
链路，不能与当前 G1J `1+2` 个单职责样本做权重结论。为遵守 GPU 0/3 边界，本轮没有在 GPU 1/2
启动或调用 G1I 服务。

## 根因与最小下一步

G1J 的 29 条新增回归中 22 条位于 S39；典型错误是在同一多步骤 Goal 中选择邻近但错误的真实操作，
例如 `make_directory -> append_file` 3 条、`read_file -> write_json` 3 条、
`write_json -> write_file` 2 条。它与已定位的 V7 输入错位一致：完整 Goal 位于续写尾部，而当前
Strong frontier 较远，Selector 被迫重新判断任务顺序。

只改一个地方时，先使用已经实现的 V8 frontier-only 投影：材料在前，Strong Planner 确定的单一
当前 objective 在最后；然后基于 G1J Hidden 重新训练匹配 Head并复跑同一 dev gate。V8 改变特征
identity，旧 Head 不能复用。只有 V8 + 匹配 Head 仍出现可复现同类错误，才把“错误输入 -> 经人工
验证的正确工具”整理为 State Tuning 候选；当前证据不支持直接 State Tuning。

确认最早失败层不需要更完整 raw trace：两份 `DEV_PREDICTIONS.jsonl` 已含 label、raw logits、
raw argmax、selected、exact 和 postprocessed。要判断某条线上 Goal 在 Selector 错误后，13.3B、
Audit 或 Stage Checker 是否产生新的独立错误，才需要打开该 Goal 的完整 causal raw trace。
