# Round23 Medium M01–M30 标准答案后逐题对比

全30题Strict/Completed均FAIL。External只有M01、M18通过；其余按标准答案、最终artifact与冻结盲审连接如下。

## E2E-M01

- **Reference/actual**：三个service及summary四项全部与标准一致，External PASS。
- **因果**：Round23成功展开api/web/worker并写对，是protocol可达性收益；之后扩到40 tasks/attempt仍0 claim/evidence，
  collection完成没有全称聚合状态。
- **R22→R23**：FAIL→PASS。Round22只更新api，本轮三个成员都执行；是Medium新增通过之一，但Strict仍无改善。

## E2E-M02

- **Reference/actual**：weighted_total仍忽略weight，测试15!=35，External FAIL。
- **因果**：RWKV已读取test仍两次写回同一错误公式；内部python ENOENT只是后续遮挡。
- **R22→R23**：持续FAIL，明确model code error。

## E2E-M03

- **Reference/actual**：source保持schema1 users，标准迁移完全未执行，External FAIL。
- **因果**：两次Goal都是6 criteria>5，0 task；未测试migration production。
- **R22→R23**：持续FAIL，cardinality gate仍是首因。

## E2E-M04

- **Reference/actual**：release JSON正确；Markdown正文正确但缺最后newline，External FAIL。
- **因果**：盲审已识别production主体正确和fan-in proof缺失；后验只新增一个byte-level尾换行错误。
- **R22→R23**：持续FAIL。

## E2E-M05

- **Reference/actual**：权威三条要求被写成通用“implement/tests/run suite”，且无尾换行，External FAIL。
- **因果**：source已正确读取，首偏离是RWKV source→plan语义生成；self-read只固化错误。
- **R22→R23**：持续FAIL。

## E2E-M06

- **Reference/actual**：package目录不存在，External FAIL。
- **因果**：Goal两次6/7 criteria超限，selection/digest能力未运行。
- **R22→R23**：持续FAIL。

## E2E-M07

- **Reference/actual**：nested trace合并正确，但port/workers仍为defaults 8000/2而非9000/4，External FAIL。
- **因果**：完整source均已观察，是RWKV recursive merge的部分语义错误；重复whole writer未修leaf mismatch。
- **R22→R23**：持续FAIL。

## E2E-M08

- **Reference/actual**：actual hallucinate auth/billing等六服务，与api/web/worker标准完全不同，External FAIL。
- **因果**：空dependencies使writer先于reader，迟到source没有使stale producer失效；之后还对Markdown用read_json。
- **R22→R23**：持续FAIL。

## E2E-M09

- **Reference/actual**：old_api implementation/call未改，外部test仍返回5而非8，External FAIL。
- **因果**：无dependencies且priority让test先运行，runtime ENOENT耗尽budget，source/writer均未执行。
- **R22→R23**：持续FAIL；protocol放行了错误Graph但未改善任务。

## E2E-M10

- **Reference/actual**：`resilient.txt`缺失且未出现replan event，External FAIL。
- **因果**：Plan在writer前读取尚不存在的target；相同missing observation重试，producer饿死。
- **R22→R23**：持续FAIL。

## E2E-M11

- **Reference/actual**：api/auth正确；jobs port应8002却8001，web port/workers应8003/3却8080/4；summary schema和值均错。
- **因果**：只读api便生成四成员，未观察成员值由RWKV猜测，59 tasks进一步固化。
- **R22→R23**：持续FAIL。

## E2E-M12

- **Reference/actual**：median通过；safe_divide(1,0)抛ZeroDivisionError而非ValueError，External FAIL。
- **因果**：T3先建立过正确实现，后续whole-file writer覆盖掉zero guard；same-target revision没有last-valid状态。
- **R22→R23**：持续FAIL。

## E2E-M13

- **Reference/actual**：row/quantity正确，但north被算22.5、grand 37.5且by_region schema嵌入quantity/revenue对象，External FAIL。
- **因果**：完整CSV可见下的直接RWKV算术/schema错误，action success被当task完成。
- **R22→R23**：持续FAIL。

## E2E-M14

- **Reference/actual**：release JSON正确；Markdown是无关v1.0.0模板，External FAIL，不是仅acceptance空行差异。
- **因果**：后一个writer虽修正JSON，却没有原子修正companion Markdown；多artifact一致性没有共同revision。
- **R22→R23**：持续FAIL。

## E2E-M15

- **Reference/actual**：line/byte/total数值全部正确，但每个path错误多了`docs/`前缀，External FAIL。
- **因果**：递归发现与计数能力存在；root-relative path contract在producer payload中理解错。
- **R22→R23**：持续FAIL。

## E2E-M16

- **Reference/actual**：recovered.json缺失，External FAIL。
- **因果**：valid/invalid primary分支没有typed outcome与per-id committed source；流程在局部分支失败中断。
- **R22→R23**：持续FAIL。

## E2E-M17

- **Reference/actual**：仅core迁移正确；worker/web未改，matrix dependencies全空，External FAIL。
- **因果**：collection只读取core，一成员action完成被升级为三成员完成。
- **R22→R23**：持续FAIL。

## E2E-M18

- **Reference/actual**：三项relative path digest逐字正确并排除self，External PASS。
- **因果**：Round22的Goal自哈希矛盾本轮未出现；artifact metadata使b/c digest对RWKV可达，但proof仍0 evidence并priority异常。
- **R22→R23**：FAIL→PASS，是Medium第二个新增产物通过；仍非Strict改善。

## E2E-M19

- **Reference/actual**：access_summary缺失，External FAIL。
- **因果**：Goal两次8 criteria且error_paths定义内部冲突，0 task。
- **R22→R23**：持续FAIL。

## E2E-M20

- **Reference/actual**：parser仍返回空数组，两个tests均失败，External FAIL。
- **因果**：Goal两次7 criteria超限，0 task；代码能力未进入执行。
- **R22→R23**：持续FAIL。

## E2E-M21

- **Reference/actual**：最终只剩`{"record_count":3}`，records全部丢失，External FAIL。
- **因果**：T3曾一次写出完整正确records；T5/T6“加count”whole-file writer覆盖为partial object。action success→task complete与
  same-target revision共同放大。
- **R22→R23**：External PASS→FAIL，是Medium唯一回归；Round22三个重复writer恰好都保留完整对象，本轮后写破坏正确state。

## E2E-M22

- **Reference/actual**：模型应用了全部四key、rejected空，并使用`applied_keys/rejected_keys`错误字段名，External FAIL。
- **因果**：config/policy/request均已观察，首因是RWKV policy application错误；5次whole write重复错误决定。
- **R22→R23**：持续FAIL。

## E2E-M23

- **Reference/actual**：只建立start.sh和manifest；README/config缺失，manifest列表还未排序，External FAIL。
- **因果**：一个plural writer只执行一个member就completed；目录reader没有反向打开missing producer。
- **R22→R23**：持续FAIL。

## E2E-M24

- **Reference/actual**：priority order test通过，duplicate test失败，External FAIL。
- **因果**：RWKV一度写lock而非duplicate set，后续whole writer又覆盖；runtime反馈未导向语义修正。
- **R22→R23**：持续FAIL。

## E2E-M25

- **Reference/actual**：用write_json把Markdown写成quoted JSON string，1.2内部又是fix在add前，External FAIL；不仅是group空行差异。
- **因果**：media type/tool choice与排序语义均错，read-back只证明错误bytes存在。
- **R22→R23**：持续FAIL。

## E2E-M26

- **Reference/actual**：valid/rejected索引整体错位，id0被判valid、id3被拒，reason集合也错，External FAIL。
- **因果**：一成员/一局部validation success被提升为全collection完成；最终payload是直接RWKV规则应用错误。
- **R22→R23**：持续FAIL。

## E2E-M27

- **Reference/actual**：actual是普通字母序api/app/core/docs/web，不满足dependency order，External FAIL。
- **因果**：RWKV把deterministic topological order误解为alphabetical whole-list sort；完整graph已观察。
- **R22→R23**：持续FAIL。

## E2E-M28

- **Reference/actual**：只copy 07-20且没有从logs删除，07-31仍被错误kept；tree/report均FAIL。
- **因果**：一个member copy被升级为“move all old files”completed；Harness无atomic move虽增加步骤，但不能解释错误cutoff成员选择。
- **R22→R23**：持续FAIL。

## E2E-M29

- **Reference/actual**：actual只含locale已有hello/save与missing_keys，丢bye/cancel fallback；无论flat或acceptance nested schema都错。
- **因果**：RWKV没有执行“保留每个base key”，是直接merge语义失败；acceptance的`translations`外层是次要口径差异。
- **R22→R23**：持续FAIL。

## E2E-M30

- **Reference/actual**：config完全未迁移、report缺失、外部verifier失败，External FAIL。
- **因果**：action-choice阶段两次已给完整合理`write_json name+arguments`，却因两段式协议被拒；随后流程未到producer。
- **R22→R23**：持续FAIL；强证据支持单次原子action proposal以减少语义重复，不代表Controller补迁移值。

## Medium组结果

- External `2/30`：M01、M18；两题仍因0 evidence/terminal异常Strict FAIL。
- 相对Round22：M01/M18新增，M21丢失，Medium从1升至2。
- 直接RWKV错误集中在M02/M05/M07/M08/M11/M13/M22/M24/M25/M26/M27/M29；零执行cardinality问题集中在
  M03/M06/M19/M20；集合/partial-completion问题集中在M01/M11/M17/M23/M26/M28；same-target破坏以M12/M21最清晰。
