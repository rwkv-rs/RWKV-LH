from pathlib import Path
import json,hashlib,subprocess,shutil
R=Path('/home/chase/GitHub/RWKV-LH');O=R/'data/experiments/R126_CURRENT_REGRESSION_REVIEW_R1_20260911'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
rows=json.loads((O/'CURRENT_20_CASE_ANALYSIS.json').read_text());s=json.loads((O/'SUMMARY.json').read_text());s['selector_boundaries']=sum(len(r['selections']) for r in rows);assert s['selector_boundaries']==86
(O/'SUMMARY.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
sel=json.loads((O/'SELECTOR_INPUT_EVIDENCE.json').read_text());b=[r for r in sel if r['task_id']=='E2E-B11'];assert len(b)==3 and all(r['selected']=='search_text' for r in b);assert all('read_file' in lane['eligible'] for r in b for lane in r['lanes'])
for r in b[1:]:assert all('obtaining its raw content' in lane['prompt'] and '"kind":"semantic"' in lane['prompt'] for lane in r['lanes'])
assert s['task_equal_90']==s['acceptance_equal_90']==90 and s['actions']==78
refs=json.loads((O/'HISTORICAL_SOURCES.json').read_text());p='data/experiments/G1J_GOAL_LOOP_V2_REAL_CAPABILITY_BASELINE_20260901/TRACE_AUDIT_AND_CAPABILITY_RESULT.md';raw=subprocess.check_output(['git','show','3ad7933a:'+p],cwd=R);refs.append({'commit':'3ad7933a','path':p,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)});(O/'HISTORICAL_SOURCES.json').write_text(json.dumps(refs,indent=2)+'\n')
for n in ['analyze_r126_current_regression_r1_20260911.py','decode_regression_selector_evidence_r1_20260911.py',Path(__file__).name]:shutil.copyfile(R/'temp'/n,O/('EVIDENCE_SCRIPT_'+n))
(O/'VALIDATION.json').write_text(json.dumps({'snapshot_cases':20,'events_recount_matches_result_action_count':True,'selector_boundaries':86,'all_90_task_and_acceptance_objects_equal':True,'b11_read_file_eligible_all_three_lanes_all_three_boundaries':True,'b11_semantic_feedback_present_after_first_action':True,'old_raw_trace_available':False,'production_changed':False,'rescore_performed':False,'training_optimizer_steps':0},indent=2)+'\n')
h=R/'docs/HANDOFF.zh-CN.md';text=h.read_text().replace('# 当前交接\n','# 当前交接\n\n## 2026-09-11 R126与当前能力退化分析\n\n已核实历史R126报告Strict36/90（提交说明复测34/90），当前原90题的任务和验收对象90/90相等，Strict核心条件也一致。当前前20题固定分析：Strict0/20、completed0/20、78动作、mutation1；15重复成功、2重复失败、3协议预算阻塞。9道属于旧90题；B01/B11/B13有历史报告级成功与当前原始失败证据。当前组合未证明架构收益，不能以测试全绿或证据完整代替能力；也不能将多变量损失全部归于Selector。具体因果链、历史原始trace缺失限制及下一步见[退化分析](../data/experiments/R126_CURRENT_REGRESSION_REVIEW_R1_20260911/REPORT.zh-CN.md)。原117题队列继续，不改评分/源码/预算，未训练。\n',1);h.write_text(text)
(O/'SHA256SUMS').write_text(''.join(f'{sha(p)}  {p.name}\n' for p in sorted(O.iterdir()) if p.is_file() and p.name!='SHA256SUMS'))
print('evidence_sha256',sha(O/'SHA256SUMS'))
