from pathlib import Path
import json,hashlib
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_FACT_CORRECTION_COMPARISON_R1_20260913';reg=json.loads((D/'REGISTRATION.json').read_text());strong=[];parents={};rows=[]
for c in reg['cases']:
 p=Path(c['parent']);assert hashlib.sha256((p/'RESULT.json').read_bytes()).hexdigest()==c['parent_result_sha256'];assert hashlib.sha256((p/'state_snapshot.json').read_bytes()).hexdigest()==c['parent_state_sha256']
 workspace=Path(json.loads((p/'state_snapshot.json').read_text())['goal']['workspace_root']);assert {str(f.relative_to(workspace)):hashlib.sha256(f.read_bytes()).hexdigest() for f in workspace.rglob('*') if f.is_file()}==c['files']
 for line in (p/'model_trace.jsonl').read_text().splitlines():
  e=json.loads(line)
  if e['type']=='model_session_generation_returned':parents[e['request_id']]=e['raw_generation']
 ad=D/'advice'/c['id'];actual=json.loads((ad/'INPUT.json').read_text());prepared=json.loads(Path(c['prepared_input']).read_text());assert actual==prepared
 events=[json.loads(l) for l in (ad/'strong_trace.jsonl').read_text().splitlines()]
 response=next(x for x in events if x['type']=='supervisor_request_returned')
 strong.append(dict(candidate=c['id'],call_id=response['call_id'],usage=response['usage'],latency_ms=response['latency_ms'],http_attempts=response['http_attempts'],advice_sha256=hashlib.sha256((ad/'ADVICE.json').read_bytes()).hexdigest(),actual_files_order=list(actual['files']),prepared_files_order=list(prepared['files']),same_payload_content=True,ordering_note='Actual order follows frozen registration files manifest. Prepared candidate semantic content matches; file object key order can differ and is not claimed byte-identical.'))
 for repeat in (1,2):
  path=D/'runs'/f'{c["id"]}-advised-r{repeat}';r=json.loads((path/'execution/RESULT.json').read_text());ref=json.loads((path/'ADVICE_REF.json').read_text());assert ref['sha256']==strong[-1]['advice_sha256'];con=r['continuation'];assert con['state_sha256']==c['parent_state_sha256'];rows.append(dict(run=r['id'],same_parent_sha256=con['state_sha256'],same_advice_sha256=ref['sha256'],termination=r['termination'],elapsed_seconds=r['elapsed_seconds']))
a=json.loads((D/'MECHANICAL.json').read_text());value=dict(runs=rows,new_rwkv_calls=a['checked_generations'],new_rwkv_logical_input_tokens=sum(c['input_tokens'] for r in a['runs'] for c in r['calls']),new_rwkv_output_tokens=sum(c['output_tokens'] for r in a['runs'] for c in r['calls']),strong=strong,strong_total_tokens=sum(s['usage']['total_tokens'] for s in strong),unique_historical_parent_calls=len(parents),historical_parent_input_tokens=sum(len(x['prompt_token_ids']) for x in parents.values()),historical_parent_output_tokens=sum(len(x['raw_token_ids']) for x in parents.values()),parent_accounting='Historical calls are not new requests; count once in unique episode history, not twice per fork. Per-qualified-task attribution must include failed candidates, parent work and advice; no currency costs without tariff.',mutation_count=0,false_work_claims=0,protocol_rejections=0,training_steps=0,currency_cost=None)
prev=json.loads((R/'data/experiments/RWKV_DOCUMENT_QA_AND_BUGCHECK_R1_20260913/FINAL_SOURCE_IDENTITY.json').read_text())['files'];assert all(hashlib.sha256((R/p).read_bytes()).hexdigest()==s for p,s in prev.items());value['regression']='Production matches prior final 1594 passed/0 skipped source exactly; no production/test edits, no redundant rerun'
(D/'ACCOUNTING.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');print({k:v for k,v in value.items() if k not in ('runs','strong')})
review={
 'numeric_relation':dict(core='正确指出相同数值之间提升关系错误并保留原始分数',issues=['把等价百分比换算新增判为违反任务；原任务和冻结外部契约不禁止这种等义表示'],adoption=['第一遍删掉关系错误，但吸收新增换算限制','第二遍保留原关系错误'],whole_answer_training_eligible=False),
 'requirements_as_implementation':dict(core='正确指出需求并非实现、实际GET501及db未使用',issues=['误称原候选未报告读取；原首句已经列明已读取两文件'],adoption=['两遍主要实现有无及状态码/db纠正成功','一遍直接复述建议含误评原读取的句子，另一遍末尾泛称其他参数均未实现'],whole_answer_training_eligible=False),
 'remaining_status_code':dict(core='正确指出实际501而非404，并要求补充有用验证建议',issues=['误称未报告读取，原首句已阅读；未指出JSON均未实现的过度概括'],adoption=['两遍都保留404错误','补充操作/建议，但第二遍把404而非501变成错误验证预期'],whole_answer_training_eligible=False)}
(D/'ADVICE_REVIEW_AND_ADOPTION.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n')
