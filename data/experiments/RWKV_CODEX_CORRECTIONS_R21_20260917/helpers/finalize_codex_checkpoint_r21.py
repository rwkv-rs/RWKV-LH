from pathlib import Path
import json,hashlib,shutil,time
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_CODEX_CORRECTIONS_R21_20260917'
import sys
sys.path.insert(0,str(R));from rwkv_lh.token_budget import tokenizer
id='CODING-10b4dce37b1ded8286ed1f0c';proofpath=D/'source_bound_validation_early_review3'/id/'VALIDATION.json';v=json.loads(proofpath.read_text());assert v['status']=='validated_candidate';assert v['checkpoint_id']=='CP-f49c4849fce74ce8';summary={'id':id,'status':'selected_early_original_boundary','checkpoint':v['checkpoint_id'],'input_checkpoint':v['input_checkpoint_id'],'input_tokens':len(v['input_token_ids']),'target_tokens':len(tokenizer().encode(v['target_text'])),'proof_path':str(proofpath),'proof_sha256':hashlib.sha256(proofpath.read_bytes()).hexdigest(),'previous_late_proof_preserved':True,'duplicate_source_counted':False,'truncated':False,'training_admitted':False};(D/'EARLY_BOUNDARY_SELECTION.json').write_text(json.dumps(summary,indent=2))
p=D/'PROGRESS.json';s=json.loads(p.read_text());s['selected_training_candidates']=30;s['selected_context_max']=max((x['input_tokens'] if x['id']!=id else summary['input_tokens'])+x['target_tokens']-1 for x in s['proofs']);s['selected_input_tokens']=sum(x['input_tokens'] if x['id']!=id else summary['input_tokens'] for x in s['proofs']);s['selected_target_tokens']=sum(x['target_tokens'] for x in s['proofs']);s['selected_all_fit_24576']=s['selected_context_max']<=24576;s['early_boundary_selection']=summary;s['as_of_unix']=time.time();p.write_text(json.dumps(s,indent=2))
report=D/'REPORT.zh-CN.md';text=report.read_text().replace('已登记改用这一真实早期边界重新验证','已改用这一真实早期边界重新验证并通过').replace('最终结果以 `EARLY_BOUNDARY_SELECTION.json` 为准。','见 `EARLY_BOUNDARY_SELECTION.json`。选择后仍为30个独立来源，输入合计283630 token、目标6485 token、最长24213 token，全部容纳于既有24576窗口，无截断；尚未完成冻结隔离门。');text=text.replace('生产 `rwkv_lh/` 和用户已有五处修改均未被本轮更改。','素数早期边界审核还出现两次人工误归因（协议拼写、转义文本）。生产 parser 与 compile 检查均证实原命令合法且可编译，两个错审被排除保留。最终只保留复杂度依据：公开上限1e8下原实现三秒超时，奇数筛候选本地约0.31秒完成；固定私有验收另已通过。不将本地运行时间与服务器时间混成性能提升比。\n\n生产 `rwkv_lh/` 和用户已有五处修改均未被本轮更改。')
# Refresh only the progress digest following the explicitly recorded selection.
import re
text=re.sub(r'(`PROGRESS.json`：SHA-256 `)[0-9a-f]+(`)',lambda m:m[1]+hashlib.sha256(p.read_bytes()).hexdigest()+m[2],text);report.write_text(text)
h=R/'docs/HANDOFF.zh-CN.md';text=h.read_text().replace('一条长输入正在用真实早期错误边界复验，不能截断','一条长输入已改用真实早期边界复验通过，30来源最长24213/24576，无截断');h.write_text(text)
for p in (R/'temp').glob('*r21*.py'):shutil.copy2(p,D/'helpers'/p.name)
# Keep source snapshots and private expected answers out of the local checkpoint commit.
paths=[]
for p in D.rglob('*'):
 if not p.is_file():continue
 rel=p.relative_to(D)
 if rel.parts[0]=='upload' or 'workspace' in rel.parts or p.name=='EVIDENCE_SHA256.json':continue
 if p.suffix in {'.json','.py','.md','.txt'} or p.name=='.gitattributes':paths.append(p)
manifest={'scope':'R21 local evidence; excludes upload copies, workspace copies and private cases','files':{str(p.relative_to(D)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}};(D/'EVIDENCE_SHA256.json').write_text(json.dumps(manifest,indent=2));print('evidence files',len(paths),'selected sources',s['selected_training_candidates'],'max tokens',s['selected_context_max'])
