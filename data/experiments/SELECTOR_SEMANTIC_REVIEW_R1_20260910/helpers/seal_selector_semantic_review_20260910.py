from pathlib import Path
import json,hashlib,shutil
R=Path('/home/chase/GitHub/RWKV-LH');O=R/'data/experiments/SELECTOR_SEMANTIC_REVIEW_R1_20260910'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):
 with p.open('x') as f:json.dump(x,f,ensure_ascii=False,indent=2);f.write('\n')
d=json.loads((O/'FINAL_DISPOSITIONS.json').read_text()); accepted={r['sample_id']:r for r in d['dispositions'] if r['decision']=='accept'}; rejected={r['sample_id'] for r in d['dispositions'] if r['decision']=='reject'}
rows=list(map(json.loads,(O/'reviewed_candidates/candidates.jsonl').read_text().splitlines()));q=list(map(json.loads,(O/'reviewed_candidates/review_queue.jsonl').read_text().splitlines()))
reviewed=[r for r in rows if r['label_authority']=='human_double_review']
if len(rows)!=162 or {r['sample_id'] for r in reviewed}!=set(accepted) or {r['sample_id'] for r in q}!=rejected:raise SystemExit('formal review membership mismatch')
if any(r['target_text']!=accepted[r['sample_id']]['target_text'] or len(r['human_reviewers'])!=2 for r in reviewed):raise SystemExit('label mismatch')
write(O/'FORMAL_EXTRACTION_RESULT.json',{'source_admission_restored':True,'candidate_count':162,'executed_fixture':60,'human_double_review':102,'original_label_approved':34,'corrected_label_approved':68,'raw_review_queue':24,'raw_review_queue_exactly_matches_final_rejections':True,'undisposed_pending':0,'candidate_quality_status':'invalid','optimizer_steps':0,'manifest_sha256':sha(O/'reviewed_candidates/manifest.json')})
(O/'REPORT.zh-CN.md').write_text('''# Selector 独立双AI语义复核 R1

本轮不产生新Agent成绩；历史关联十五题 Strict 0/15、completed 0/15、mutation 6不改评分。角色数据审阅完成不等于Agent能力通过。

按owner明确授权，两名独立AI reviewer分别查看44个真实前动作边界的126条菜单行，首轮互不读取对方决定。各自均报告46原标签、68纠正、12拒绝，但拒绝的行不同；对账严格执行一票拒绝、最终操作标签必须一致。最终34保留原标签、68纠正、24剔除，未处置待审=0。没有劝服改签，没有填造action evidence refs。

204条accept review附件逐一绑定输入SHA、目标SHA、原输出记录SHA、request/run/boundary、原rationale和reviewer身份。纠正目标由当前Selector协议常量形成并经parse_target与eligible_labels校验，实际输入/token重建仍走唯一生产提取器。附件只增加到原14来源注册；去附件后与原注册精确相等，同一十文件waiver、固定role和范围不变。两名reviewer另行确认这一限定附件的proposal与wrapper精确SHA。

固定wrapper正式重提取162条候选：60原自动准入+102双审；68纠正均与共同决定精确一致。原始提取器review_queue仍含24条，逐一对应最终reject；这是原始拒绝证据，不是24条未做的人工工作。未把reject注入human_reviews或改写为接受。来源准入通过，质量仍INVALID。预注册相似度处置另见SELECTOR_SIMILARITY_POLICY_R1_20260910；首轮StateTune仍需全部数据门通过，optimizer steps=0。
''')
(O/'helpers').mkdir(exist_ok=True)
for n in ['prepare_selector_semantic_review_20260910.py','reconcile_selector_reviews_20260910.py','prepare_reviewed_scope_addendum_20260910.py','seal_selector_semantic_review_20260910.py']:shutil.copyfile(R/'temp'/n,O/'helpers'/n)
files=[{'path':str(p.relative_to(O)),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(O.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.name!='EVIDENCE_SHA256.json']
write(O/'EVIDENCE_SHA256.json',{'round':O.name,'files':files,'production_commit':'21c0cf45d519ee090742c08156cd2935d112b87b','pytest_passed':1455,'optimizer_steps':0})
print(json.dumps({'report_sha256':sha(O/'REPORT.zh-CN.md'),'evidence_sha256':sha(O/'EVIDENCE_SHA256.json'),'files':len(files)}))
