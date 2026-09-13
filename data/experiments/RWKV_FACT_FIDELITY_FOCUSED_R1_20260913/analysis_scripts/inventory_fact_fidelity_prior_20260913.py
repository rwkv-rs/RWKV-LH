from pathlib import Path
import json,hashlib
R=Path('/home/chase/GitHub/RWKV-LH');Q=R/'data/experiments/RWKV_DOCUMENT_QA_AND_BUGCHECK_R1_20260913';D=R/'data/experiments/RWKV_FACT_FIDELITY_FOCUSED_R1_20260913'
rows=[]
for phase in ['file_scope_probe','requested_advice_probe','advice_label_probe']:
 for p in sorted((Q/phase/'runs').glob('*/execution/RESULT.json')):
  cid=p.parent.parent.name.rsplit('-',2)[0]
  if cid not in ('rag_overview','api_bug'):continue
  result=json.loads(p.read_text());review=Q/phase/'reviews'/f'{p.parent.parent.name}.judgment.json';j=json.loads(review.read_text())
  rows.append(dict(run=p.parent.parent.name,result_path=str(p.relative_to(R)),result_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),review_path=str(review.relative_to(R)),review_sha256=hashlib.sha256(review.read_bytes()).hexdigest(),findings=j['findings'],note='历史评分不变，已读内容与执行证据详见原始trace；不是训练样本或纠正答案'))
(D/'PRIOR_FAILURE_REFERENCES.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
