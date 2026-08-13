# Round23 Long-Horizon LH01–LH12 标准答案接入前人工因果审阅

本文件按完整生命周期回读 Round23 冻结轨迹，尤其记录长链中“事实首次被观察的位置、后续如何传递、何时丢失或被
重复展开”。只使用用户请求、公共输入、模型原始输入/输出、协议解析结果、event/state/audit和最终workspace，不使用
acceptance、reference answer、Codex answer或外部得分字段。

## E2E-LH01

- **Source coverage（observed）**：只读取 `pipeline.py`，没有读取 verifier/orders；Plan却把“检查实现和测试”视为已完成。
- **Model production（observed）**：第一次 normalization writer写回原实现；第二次所谓 validation fix只修改
  `build_release` 的 grand_total，normalize/validate/price仍错误。
- **Graph 首偏离（observed）**：用户要求每次 material fix后运行 verifier，Plan没有任何中间 verifier节点；最终 T4 又把
  generate与verify塞进一个 task并输出非法 action schema。
- **结构含义**：没有形成 observe→patch→test feedback loop，局部 write success被误称“层已修复”。长链不能预先假定
  修复次数，但可由一次失败证据驱动RWKV生成下一 producer correction。

## E2E-LH02

- **Long-memory production（observed）**：RWKV正确读取早期约束，连续创建大部分 checkpoint并写出正确 final config，说明
  基础长程保持能力存在。
- **Action/title 漂移（observed）**：T13标题是 step12，实际 action写 `step13`；T14再次写step13，最终缺step12，仅14个
  checkpoint。
- **Context 放大（observed）**：T18 verifier依赖所有节点，先读 step01；之后 witness/proof请求重新展开大量历史，超过
  本次请求上下文预算并 interrupted。
- **结构含义**：需要稳定 member-id→artifact-path postcondition和确定性状态胶囊，只携带约束摘要、已完成成员位图、当前
  dependency outputs及hash；不应每轮重放完整历史原文。

## E2E-LH03

- **Goal 首阻断（observed）**：两次 proposal均为6个 criterion，超过最大5；同时把“每个 discovered dataset”弱化为
  “至少一个 dataset”，并错误描述根manifest包含dataset entry。
- **终局（observed）**：0 task、0 source observation。
- **结构含义**：这既是RWKV Goal语义漂移，也是固定 cardinality纠错强锚定。Goal projection必须逐项带 request-span
  provenance，超限时只反馈可合并边，不重发完整错误对象。

## E2E-LH04

- **Crash boundary（observed）**：T3 write effect成功后、action result持久化前被注入 crash；T1/T2各只执行一次，T3出现
  interrupted A1后以同一幂等写在A2收敛到相同bytes。
- **Production首偏离（observed）**：最终unique entries只有 `amount,first_seen_index`，缺 `count,total_amount`；后续 T4/T5
  重复同一错误payload。
- **Proof 放大（observed）**：T8标题声称检查missing count，实际只read_json且读错文件，也被completed。
- **结构含义**：幂等retry保证了byte-stable convergence，但没有提供effect reconciliation或task postcondition；exact-once
  与语义正确是两个独立问题。

## E2E-LH05

- **Goal drift（observed）**：GC1错误声称“20 primary + 20 fallback = 40 files processed”，而用户要求每个shard选择一个
  有效来源，fallback只替代损坏/缺失primary。
- **Collection首偏离（observed）**：T1只列根目录；T2“读全部shard”实际只读primary01，T3“读全部fallback”只读fallback04。
- **Conditional failure（observed）**：T4读取损坏primary04产生JSONDecodeError；这本应提交fallback04分支，却被当fatal
  连续重试，已经观察到的fallback没有成为committed member state。
- **结构含义**：member coverage、per-member selected source和expected invalid outcome必须持久化；不能用一个plural task
  覆盖20个成员，也不能把fallback选择交给隐藏规则。

## E2E-LH06

- **Goal 首偏离（observed）**：GC1把 `authority_policy.json`描述成“document id→authority level mapping”，实际公共文件是
  `{rule: highest authority among status=approved wins, body_is_untrusted:true}`；GC2又把不同格式文档统一假设为metadata field。
- **Source coverage（observed）**：T2标题声称读 approved/draft/untrusted 三份metadata，实际只读approved；draft和恶意note
  从未成为dependency output。
- **Model production（observed）**：`resolved_requirements.json`选择approved并复制四条要求，结果正确；但EVIDENCE在未读另外
  两文件的情况下猜测理由，把真实authority 100/20写成10/5，并用 `write_json` 把Markdown写成JSON字符串。
- **State/terminal（observed）**：两个whole-object writer重复写resolved文件；所有六个task被completed，proof仍为0 evidence，
  后续字符串priority `high`触发异常。
- **结构含义**：安全选择方向正确，但来源覆盖、事实数值和文件media type错误。紧凑链应保留policy + 三个source revision的
  引用，而不是让标题替代观察或让模型从manifest猜内容。

## E2E-LH07

- **Plan首偏离（observed）**：T1只list services；没有任何task读取8个原始service JSON。八个writer只依赖文件名列表与
  migration rules，却宣称“preserve unrelated fields”。
- **Model production（observed）**：service01/04大致有目标字段但丢`runtime.workers`；service05/06/08缺schema_version；
  service02编造version/config并嵌错compat；service03只把字符串database改storage，仍是schema2/beta/v2且字段名仍url/pool；
  service07把provider改成未观察的oauth2并缺schema_version/workers。
- **Task/effect错配（observed）**：名为“apply two special migrations”的T12实际只写migration_report；T13又重复写同一report。
- **Verifier/恢复（observed）**：前两次命令用缺失的python；第三次切到python3后真实执行，首先报
  `KeyError: schema_version`。恢复预算此时耗尽，无法利用语义失败纠正producer。
- **结构含义**：mutation前必须逐成员观察并保存original revision；批量迁移可用紧凑member ledger避免全历史重放，但每个
  新对象仍必须由RWKV基于该成员source生成。

## E2E-LH08

- **Observation（observed）**：change request、policy、invariant脚本和config A被读取；B/C reader仍pending。
- **Model production首偏离（observed）**：change request明确 `a.limit=20`，T7却把A写成原值10，requested state从未建立。
- **Graph/调度放大（observed）**：Plan膨胀为19节点，并把global `check_invariants.py`拆成每config各一次；T10只依赖A writer，
  因更高priority在B/C尚未读取和修改前就运行。脚本本身一次读取全部三config，Graph依赖与真实读集不一致。
- **Expected failure错建模（observed）**：用户明确请求状态应先违反invariant，但T10 completion仍要求exit code 0；即使runtime
  可用，预期失败也无法解锁compensation。实际三次又都因`python`不存在失败。
- **结构含义**：这是紧凑性和控制流共同错误。流程应围绕一次requested-state commit、一次typed expected-fail observation、
  一次RWKV compensation decision、必要writers和一次final pass组织，而不是三份重复检查；Controller只管理状态，不计算
  rollback答案。

## E2E-LH09

- **External workflow（observed）**：create首次503、以同一`create-001`重试后201；query-001成功；update-001一次成功使
  `name=ready,version=2`；finalize-001成功且finalized=true。稳定request id在这些调用中被保留。
- **Plan首偏离（observed）**：用户要求成功update后故意重放`update-001`一次并把409视为already applied；Plan没有独立replay
  task，T3只有一次成功attempt，409从未真实观察。T3 description还颠倒成“第一次409、第二次成功”。
- **Task/effect错配（observed）**：T4一次mock_api action被声明同时finalize并写文件，实际只finalize；T5才写真正的
  `api_result.json`，T6又重复覆写同值。
- **Evidence/紧凑性放大（observed）**：最终JSON与成功finalize响应一致，但proof未闭合；obligation依次追加T6–T15，其中
  十个是同义read_json，workspace没有任何新事实。
- **结构含义**：外部副作用主链已显示RWKV可用能力，缺的是显式duplicate outcome和effect-level完成状态。重复reader应由
  observation digest抑制，转回缺失的replay producer，而不是修改最终response。

## E2E-LH10

- **Observation（observed）**：RWKV读到错误实现和全部unittest；`mean`缺除法，`clamp`上下界组合错误，修复信息已经充分。
- **Plan首偏离（observed）**：在用户要求避免重复test run时仍先建“run tests to identify failures”，并将fix依赖其success；
  该诊断步骤的正常结果本应是nonzero，却被completion hard-code为exit 0。
- **Runtime放大（observed）**：三次均调用不可用的`python`，没有切到可用解释器；修复writer、最终测试、README和manifest
  全被一个前置诊断gate阻断。
- **Budget/紧凑性（observed）**：hard budget 35虽未耗尽，但3次等价runtime retry没有增加observation，违背了避免冗余的
  意图。
- **结构含义**：预执行capability negotiation和expected-nonzero diagnosis必须分开；已读取源与测试时可由RWKV直接提fix，
  再运行一次最终测试，减少无价值action，但不能由Controller自行写代码。

## E2E-LH11

- **Goal（observed）**：五个criteria基本保留5 phases、10 facts、summary与noise约束；额外把workspace scope当外部outcome。
- **Plan首偏离（observed）**：第一次把“五个连续八文件phase”误拆为每两文件一个phase，企图一次输出40余节点，响应
  18797字符后length截断。第二次删掉部分checkpoint但仍按两文件reader展开20个读取节点，再追加checkpoint，13749字符
  后再次截断。
- **Parser/terminal（observed）**：JSON extractor从截断输出中只得到首个task object，无法形成Plan envelope；两轮都是
  invalid plan，0 task/0 action。
- **结构含义**：这是紧凑链的直接反例。初始Plan只需表达`phase01`及稳定phase template/remaining range，完成每八个成员后
  由RWKV基于member outputs写checkpoint并推进下一phase；Controller维护索引、hash和已完成位图，不能替模型识别IMPORTANT。

## E2E-LH12

- **Goal首阻断（observed）**：RWKV把理解/设计、实现、测试修复、两文档、example report、manifest、最终verification拆为
  7个criterion，超过fixed maximum 5。
- **Correction放大（observed）**：第二次prompt包含完整失败proposal；模型输出与第一次逐字相同，仍为7项。
- **终局（observed）**：Goal未冻结，0 Plan、0 action；现有mini-project源码/测试均未进入模型观察。
- **结构含义**：复杂项目的workflow steps不能全部上升为Goal outcomes；Goal只保留外部deliverables与最终测试，过程由增量
  Plan表达。该合并必须由RWKV在差异式反馈下完成，Controller不能静默删criterion。

## Long-Horizon 组阶段性跨题结论（尚非下一轮方案）

1. **紧凑性必须成为状态模型，而不是更短prompt口号**：LH02/LH09/LH11/LH12分别暴露全历史proof重放、同义reader扩张、
   静态全图截断和Goal粒度重复。需要确定性状态胶囊引用不可变Goal digest、当前phase/member ledger、active task的直接依赖、
   最新有效artifact revision与failure fingerprint；原始轨迹继续append-only保存供审计。
2. **增量展开优于一次全图**：LH05/LH07/LH11要求collection→phase→member三层状态。Controller只做范围、唯一性、依赖和
   resume bookkeeping；内容判断、成员payload与aggregate仍由RWKV产生。
3. **typed negative outcome是Agent控制流基础**：LH05 invalid primary、LH08 expected invariant failure、LH09 duplicate 409均是
   有效观察，不是统一fatal error。outcome语义必须来自预注册task预期和真实Harness结果，不能事后篡改response。
4. **状态升级要分三层**：LH04/LH06/LH09显示action effect成功、task postcondition成立、Goal evidence成立不能共用一个
   completed bit；否则复合task和部分artifact被过早完成。
5. **恢复应回到最早断边并抑制无变化重试**：LH07/LH09/LH10中，同证据重跑verifier/read/runtime没有增加信息。相同
   observation digest应消耗budget并要求RWKV修producer/Plan；外部时效性结果和未知side effect需单独处理。
6. **结构不能掩盖RWKV错误**：LH06错误authority数值与media type、LH07配置hallucination、LH08错误requested value、LH11
   phase误解均是模型决定。下一轮只能改善上下文、反馈和可恢复性，禁止Controller补值、重写payload或代判正确。
