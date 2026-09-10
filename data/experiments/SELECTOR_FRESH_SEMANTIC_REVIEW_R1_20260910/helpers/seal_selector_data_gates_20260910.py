from pathlib import Path
import json,hashlib,shutil
R=Path('/home/chase/GitHub/RWKV-LH');E=R/'data/experiments'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def write(p,o):
 with p.open('x') as f:json.dump(o,f,ensure_ascii=False,indent=2);f.write('\n')
F=E/'SELECTOR_FRESH_SEMANTIC_REVIEW_R1_20260910';S=E/'SELECTOR_SIMILARITY_POLICY_R1_20260910';T=E/'SELECTOR_TRAINING_PREFLIGHT_R1_20260910'
(F/'REPORT.zh-CN.md').write_text('''# 新采集43行的独立AI语义复核

关联新四题Agent Strict 0/4、completed 0/4、mutation 0，三题重复动作阻塞、一题协议拒绝阻塞；本轮语义标签处置不改变Agent评分。

沿用owner授权的独立双AI数据门流程，额外完成新采集15真实边界、43行复核。两review首轮互不读对方决定；按同一一票否决/操作标签一致规则，18保留原标签、16纠正、9剔除，待审0。原始43队列不改写；两个AI在部分边界对操作归因不一致，未要求改签。

68条review附件pin精确输入、目标、原输出、边界和每人的原始rationale，新四来源全部绑定21c0cf45源码，不使用waiver。生产重新提取48候选（14自动+34双审）、9原始review_queue行与最终reject精确对应。execute仍0，不虚构command执行或训练正例。来源/标签审阅完成，质量INVALID；optimizer steps=0。
''')
(S/'REPORT.zh-CN.md').write_text('''# Selector相似度策略 R1

本数据轮无新Agent分数；关联四题为Strict 0/4、completed 0/4、mutation 0，三题无进展、一题协议拒绝。去重合格不代表Agent能力改善。

运行前预注册保留原始project-family哈希切分、完整UTF-8 byte5gram count cosine、阈值>=0.95，精确整数比较；以真实selection boundary及其菜单行为单位建连通分量。涉及原5条开发/确认anchor的分量剔除全部train；纯train分量仅保留(source_run_id,run_id,boundary_event_id)字典序最小单元。没有更改输入、阈值、family、评分或把train移入验证集。

原60自动候选按该规则保留14（9/3/2），原101/281跨切分超相似对清零。加入102双审标签后162→20；新采集14自动加入后176→20；再加入新34双审后最终210→20，训练/开发/确认=15/3/2，7分量，190行按完整身份排除，原5anchor全字段不变，最终跨切分超相似对=0。所有中间结果均保留，不因最终覆盖不足更换代表行。

最终required flags：mutate9、py_root9、missing_target6、execute0。非空切分与相似度门通过，required coverage失败，候选仍INVALID。没有发布虚假的regression fingerprint或正式角色数据集；也未把33条语义reject算作未复核。原始审阅共169条均已处置，136共同接受（52原标签+84纠正）、33剔除。完整排除原因见final210.EXCLUSIONS.json。

当前冻结入口未支持waiver与此已注册筛选规则的再现，需单独接线修复而不能跳过重提取；细节见SELECTOR_TRAINING_PREFLIGHT_R1_20260910。optimizer steps=0。
''')
old=list(map(json.loads,(S/'reviewed162/candidates.jsonl').read_text().splitlines()));new=list(map(json.loads,(S/'final210/candidates.jsonl').read_text().splitlines()));same=old==new
final=read(S/'final210/manifest.json'); pre=read(T/'DATA_PREFLIGHT.json')
write(T/'FINAL_GATE.json',{'final_candidate_manifest':{'path':str(S/'final210/manifest.json'),'sha256':sha(S/'final210/manifest.json')},'final_rows_equal_to_normalized_preflight':same,'source_and_semantic_review_complete':True,'original_pending':0,'fresh_pending':0,'cross_split_similarity_passed':True,'execute_coverage':0,'data_status':final['status'],'zero_source_profiles_and_tokenizer_verified':same and pre['normalization_failures']==0 and pre['all_input_profiles_zero'],'freeze_reproduction_integration_ready':False,'prior_regression_triple_pin_ready':False,'training_run_registered':False,'optimizer_smoke_started':False,'optimizer_steps':0,'reason':'Required execute coverage missing; independently confirmed freeze reproduction lacks waiver and registered row filtering. No source mutation during the budget experiment; no fabricated prior-regression.'})
(T/'REPORT.zh-CN.md').write_text('''# Selector首轮训练前置检查 R1

关联新采集Agent Strict 0/4、completed 0/4、mutation 0，三题无进展、一题协议拒绝；低分本身不构成禁止训练的理由。

已完成来源精确waiver与新源码直接准入、旧126+新43独立双AI复核处置、预注册相似度处理。最终20条=15train/3dev/2confirmation，与已用生产normalize_row检查的20条逐行相同，20/20完整token/BOS/目标/协议/模型/长度校验通过。源State全部zero，tokenizer SHA e6dee3d4e31b4d5c40ac99508ac6c701ceef4bed681bf2167ce9a908552bca89，模型SHA1f920b94c4684e8463f36d8b71df23a8b50551f7776d39eec9ec6970471d460b。这里是源数据检查，不能替代优化器smoke与训练时zero-State注入attestation。

尚未满足的实际条件：execute覆盖=0，候选status=invalid，因此当前流程未发布合格固定regression，--prior-regression/--regression-sha256/--expected-regression-fingerprint三重pin未就绪。保留原5条候选anchor并不等于伪造一份合法回归。

此外代码审查确认rwkv_lh/statetune_data.py的freeze_dataset在第117行重新调用trace.extract_registration时，只传role/prior regression/fingerprint，没有传已双签waiver或预注册行筛选规则，随后要求整个manifest完全相等。即使补上execute，也不能将当前派生候选直接冻结：缺少source_registration身份的筛选派生manifest会先被拒绝，原waiver来源又会在复验遭SHA拒绝。应在采集/预算两臂结束后作为独立集成修复，保留精确pin、双签范围和完整重建；不得采用自建训练文件或跳过复验。相关源码SHA见DATA_PREFLIGHT.json。

故本轮不登记“已开始”的Selector训练、不新建data/datasets角色版本，不跑optimizer smoke；optimizer steps=0。owner授权仍有效，未要求再次授权。后续先恢复可再现的合法冻结通道与真实execute来源，全部门通过后按已授权流程登记具体预算/State/模型/数据/训练器SHA，再执行smoke和首轮训练。
''')
helpermap={F:['prepare_fresh_selector_semantic_review_20260910.py','present_fresh_selector_semantic_review_20260910.py','reconcile_and_extract_fresh_selector_review_20260910.py','reconcile_fresh_selector_reviews_20260910.py'],S:['preregister_selector_and_executor_rounds_20260910.py','apply_selector_similarity_policy_20260910.py'],T:['preflight_selector_training_data_20260910.py']}
for folder,names in helpermap.items():
 (folder/'helpers').mkdir(exist_ok=True)
 for name in names:shutil.copyfile(R/'temp'/name,folder/'helpers'/name)
 shutil.copyfile(R/'temp/seal_selector_data_gates_20260910.py',folder/'helpers/seal_selector_data_gates_20260910.py')
 files=[{'path':str(p.relative_to(folder)),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(folder.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.name!='EVIDENCE_SHA256.json']
 write(folder/'EVIDENCE_SHA256.json',{'round':folder.name,'files':files,'production_source':'21c0cf45','pytest_passed':1455,'optimizer_steps':0})
 print(json.dumps({'round':folder.name,'report_sha256':sha(folder/'REPORT.zh-CN.md'),'evidence_sha256':sha(folder/'EVIDENCE_SHA256.json')}))
