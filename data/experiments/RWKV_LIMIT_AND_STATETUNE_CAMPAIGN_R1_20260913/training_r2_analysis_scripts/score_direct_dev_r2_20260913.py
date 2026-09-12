from pathlib import Path
import json,hashlib
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_LIMIT_AND_STATETUNE_CAMPAIGN_R1_20260913/evaluation_r2'
packets=json.loads((D/'DEV_REVIEW_PACKETS.json').read_text()); reviews=[]
for p in packets:
 central=1 if p['id']=='8d80eee76260' else 2
 note='主旨、重要行为与限制有用且忠实；一般实现细节允许省略。'
 if central==1:note='准确说明预约操作、防冲突与持久化，但没有说明并发判定与写入的原子约束，也未提健康检查的验证边界；前者是冻结的重要行为要求，因此属于部分覆盖，不是错误完成。'
 if p['id']=='56b1f36b0929':note='全文复述，压缩性欠佳；按冻结内容/忠实性规则通过，单列摘要形式局限，不追加运行后否决项。'
 if p['id']=='6049a1616b32':note='健康检查、未实现路由和启动参数准确；适合快速搭建和测试属于泛化评价，记为不必要评论，不当作具体已实现功能的捏造。'
 if p['id']=='a73d68b29e9a':
  assert len(p['file'].encode())==935 and len(p['file'].splitlines())==22
  note='HTTP主旨、路由和启动准确；935字节/22行与原文件相符，属于冗余元数据；配置数据库路径指命令行参数，没有宣称数据库已连接。'
 reviews.append(dict(id=p['id'],answer_sha256=hashlib.sha256(p['final'].encode()).hexdigest(),subject=1,central_meaning=central,fidelity=2,false_work_completion=False,note=note,reviewer='Codex external source-based dimensional review before arm mapping'))
mapping=json.loads((D/'DEV_REVIEW_MAPPING.json').read_text());mechanical={r['run']:r for r in json.loads((D/'DEV_MECHANICAL.json').read_text())}
for r in reviews:
 m=mechanical[mapping[r['id']]];r.update(run=m['run'],arm=m['arm'],repeat=m['repeat'],complete_read=m['complete_read'],termination=m['termination']);r['task_pass']=m['complete_read'] and m['input_and_state_verified'] and m['workspace_unchanged'] and (r['subject'],r['central_meaning'],r['fidelity'])==(1,2,2)
summary={arm:{'tasks':8,'task_pass':sum(r['task_pass'] for r in reviews if r['arm']==arm),'submitted':sum(m['submitted'] for m in mechanical.values() if m['arm']==arm),'complete_read':sum(m['complete_read'] for m in mechanical.values() if m['arm']==arm),'calls':sum(len(m['calls']) for m in mechanical.values() if m['arm']==arm),'terminations':{t:sum(m['termination']==t for m in mechanical.values() if m['arm']==arm) for t in sorted({m['termination'] for m in mechanical.values() if m['arm']==arm})}} for arm in ['zero','candidate']}
for name,v in [('DEV_REVIEWS.json',reviews),('DEV_SUMMARY.json',summary)]:
 p=D/name;assert not p.exists();p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
print(summary)
