# Round23 Long-Horizon LH01–LH12 标准答案后逐题对比

12题Strict/Completed/External全部FAIL。部分子结果正确，但没有一题同时完成产物、验证与生命周期要求。

## E2E-LH01

- **Reference/actual**：pipeline仍在normalize首层失败，release artifact缺失；阶段verifier attempt_count=0。
- **因果**：只读pipeline未读orders/verifier；两次writer只局部/原样修改，Plan又没有“每次material fix后验证”的反馈循环。
- **R22→R23**：持续FAIL；本轮未建立逐层correction loop。

## E2E-LH02

- **Reference/actual**：final config六字段完全正确；15个checkpoint仅缺step12，External整题FAIL。
- **因果**：step12 title/action漂移到step13，后一个task再次写step13；后续proof全历史展开导致context overflow。
- **R22→R23**：持续FAIL，但这是明确near-success：长程约束保持正确，失败集中于member identity与紧凑状态传递。

## E2E-LH03

- **Reference/actual**：global_index缺失，External FAIL。
- **因果**：Goal两次6 criteria>5，且语义把“every dataset”弱化；0 task。
- **R22→R23**：持续FAIL。

## E2E-LH04

- **Reference correction/actual**：acceptance要求unique首event数组加顶层count3/total13；actual数组含first_seen_index且缺外层。
  Event 41直接证明post-effect crash发生，T3-A1 interrupted后同fingerprint T3-A2成功；但run未完成，runner的
  `post_effect_crash_resumed`/completed-noop验收均false。
- **因果**：幂等写使未知effect重试收敛相同bytes，但task postcondition和最终schema错误；后续writer重复错误payload。
- **R22→R23**：持续FAIL；不能把“crash retry可恢复”夸大成“完整lifecycle通过”。

## E2E-LH05

- **Reference/actual**：reports目录、summary和REPORT全部缺失，External FAIL。
- **因果**：一个plural reader各只读一个primary/fallback；invalid primary04本应commit fallback04，却被当fatal重试。
- **R22→R23**：持续FAIL。

## E2E-LH06

- **Reference/actual**：四条requirements及approved path语义正确；acceptance只因key应`source`而actual用
  `authoritative_source`使JSON check FAIL。EVIDENCE包含approved、未含acceptance字样、无scope violation三项PASS；但文件是
  JSON-encoded Markdown string、authority数字10/5错误且draft/untrusted从未读取。
- **因果**：不是单纯“隐藏key导致误杀”；source coverage与media type仍有真实错误，proof最后priority异常。
- **R22→R23**：持续FAIL。

## E2E-LH07

- **Reference/actual**：8个文件均存在但有11项migration violation；report内容列表对但key services≠migrated；python3 verifier
  因缺schema_version失败。
- **因果**：Plan从未读取任一service内容，whole writers猜值并丢workers/schema；T12“special migration”实际只写report。
- **R22→R23**：持续FAIL。

## E2E-LH08

- **Reference/actual**：A/c恰为最终rollback值而PASS；最高priority B仍40应70，compensation缺失，最终verifier失败；预期
  `capacity invariant violated`阶段也未观察。
- **因果**：A writer没有应用request而写原值；全局check在B/C writer之前运行，且expected failure仍要求exit0。
- **R22→R23**：持续FAIL。

## E2E-LH09

- **Reference/actual**：create 503 retry、query、update、finalize均成功，resource/finalized语义正确；但没有重放update-001，
  duplicate_conflicts=0应1。api_result另有status/operation导致acceptance exact JSON FAIL，该额外字段是口径收窄而非主流程错误。
- **因果**：Plan缺独立duplicate replay node；T4复合effect被提前completed，之后十个同义reader造成无信息扩张。
- **R22→R23**：持续FAIL；这是最接近完整external workflow的一题，但明确少一个用户要求的真实side effect observation。

## E2E-LH10

- **Reference/actual**：mean/clamp仍为原错误，tests两项FAIL；README/manifest缺失。attempt 5≤35仅证明未超budget，不代表任务进展。
- **因果**：前置diagnostic test用不可用python三次并要求exit0，fix task被success dependency阻断。
- **R22→R23**：持续FAIL。

## E2E-LH11

- **Reference/actual**：0 attempt，五checkpoint及summary全部缺失，External FAIL。
- **因果**：两次静态全图均把八文件phase误拆成两文件节点并length截断；parser只抽到首task，Plan无效。
- **R22→R23**：持续FAIL；最直接证明需要phase/member增量展开和紧凑状态胶囊。

## E2E-LH12

- **Reference/actual**：源码仍NotImplemented，tests ERROR；report/docs/manifest全部缺失。
- **因果**：Goal两次逐字重复7 criteria>5，0 task。
- **R22→R23**：持续FAIL。

## Long-Horizon结果

- External `0/12`；LH02 final config、LH06 requirements主体、LH09 external API大部分流程是正确子结果，但各自缺checkpoint、
  真实source/EVIDENCE或duplicate replay。
- 长链最共同的结构缺陷不是工具数量，而是：静态全图、复合task、typed negative outcome缺失、member identity丢失、全历史
  重放及action/task/goal状态混用。
- 这些题也保留了真实RWKV错误：LH06猜authority/media type、LH07配置hallucination、LH08不应用requested值、LH11 phase误解。
  下一轮结构只能缩短反馈链、增加可恢复状态，不能替模型改答案。
