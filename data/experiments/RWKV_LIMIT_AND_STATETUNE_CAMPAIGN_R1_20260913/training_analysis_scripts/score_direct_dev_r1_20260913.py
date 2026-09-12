from pathlib import Path
import json,hashlib
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_LIMIT_AND_STATETUNE_CAMPAIGN_R1_20260913/evaluation';packets=json.loads((D/'DEV_REVIEW_PACKETS.json').read_text());mapping=json.loads((D/'DEV_REVIEW_MAPPING.json').read_text());mechanical={r['run']:r for r in json.loads((D/'DEV_MECHANICAL.json').read_text())};reviews=[]
notes={
'34061c227757':'准确概括健康检查与其不认证事务功能的边界；超时/关闭连接可省略。',
'50810c383177':'准确概括HTTP入口、健康端点和未实现占位、参数及启动；没有宣称数据库功能，db未使用无需强制提及。',
'52da49cade96':'简短但含健康检查操作、通过条件与不验证预约/订单的限制。',
'5e1fb8ecaf79':'全文复述较长，摘要压缩性欠佳；主旨、重要事务/幂等/持久性与事实全部正确，冻结评分没有长度/压缩比否决项，不事后添加。',
'783e02435a1a':'包含预约目的、操作、防冲突、原子写入和持久性，省略某些API细节不影响主旨。',
'a2b66fc27370':'库存/订单、幂等、原子失败、并发防超卖、持久化与验证边界准确。',
'ef071e3fe9e0':'预约目标、CRUD/取消、防冲突、并发原子性与恢复要求准确。',
'f3a05cabc24c':'HTTP入口主旨和健康路由正确，但虚构启动时打印docstring，并把serve_forever的服务器本身说成后台线程运行；无依据具体事实使忠实性不合格。'}
for p in packets:
 final=p['final'];faith=1 if p['id']=='f3a05cabc24c' else 2 if final is not None else 0;review={'id':p['id'],'answer_sha256':hashlib.sha256((final or '').encode()).hexdigest(),'subject':int(final is not None),'central_meaning':2 if final is not None else 0,'fidelity':faith,'false_work_completion':False,'note':notes.get(p['id'],'没有提交总结；按未完成评分，不将final_answer提交或缺失细节冒称虚假工程完成。'),'reviewer':'Codex external source-based review; arm mapping applied after dimensional review'};reviews.append(review)
for r in reviews:
 m=mechanical[mapping[r['id']]];r.update(run=m['run'],arm=m['arm'],repeat=m['repeat'],complete_read=m['complete_read'],termination=m['termination']);r['task_pass']=m['complete_read'] and m['input_and_state_verified'] and m['workspace_unchanged'] and (r['subject'],r['central_meaning'],r['fidelity'])==(1,2,2)
summary={arm:{'tasks':8,'task_pass':sum(r['task_pass'] for r in reviews if r['arm']==arm),'submitted':sum(m['submitted'] for m in mechanical.values() if m['arm']==arm),'complete_read':sum(m['complete_read'] for m in mechanical.values() if m['arm']==arm),'calls':sum(len(m['calls']) for m in mechanical.values() if m['arm']==arm),'terminations':{t:sum(m['termination']==t for m in mechanical.values() if m['arm']==arm) for t in sorted({m['termination'] for m in mechanical.values() if m['arm']==arm})}} for arm in ['zero','candidate']}
for name,value in [('DEV_REVIEWS.json',reviews),('DEV_SUMMARY.json',summary),('DEV_GATE.json',{'passed':False,'reason':'candidate 0/8, repeat-read loops and illegal read calls; not eligible for confirmation or production retention','read_regression':'not run for rejected candidate; frozen cases retained','confirmation':'not run; no confirmation result inspected'})]:
 p=D/name;assert not p.exists();p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
print(summary)
