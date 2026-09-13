from pathlib import Path
import sys,json,shutil
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R))
from rwkv_lh import task_review as v
Q=R/'data/experiments/RWKV_DOCUMENT_QA_AND_BUGCHECK_R1_20260913';D=R/'data/experiments/RWKV_SOURCE_ATTRIBUTION_CONTROL_R1_20260913';D.mkdir()
reg=json.loads((R/'data/experiments/RWKV_FACT_FIDELITY_FOCUSED_R1_20260913/REGISTRATION.json').read_text());reg['round']=D.name
reg['source_pins']={p:v.file_digest(R/p) for p in reg['source_pins']};reg['execution_identity']['source']=v.digest(reg['source_pins'])
reg['cases']=[];reg['order']=[['focused',1],['focused',2]]
reg['question']='Does adding a real requirements README alongside identical server.py change attribution of implemented code behavior? Source list and available files vary; core question stays fixed. Reading choices remain RWKV-owned.'
reg['comparison_limit']='Small source-availability diagnostic, not universal causal proof or prompt repair gain. Task source-list wording differs with availability. Require actual complete read of named sources before attributing an effect to added README. No forced ordering, no reference facts in input.'
reg['gate']='Each arm two repeats all essential requirements met, no material unsupported claims or false work claims; broader task and reading gates remain separate.'
core='以 server.py 源码为依据，说明实际实现了哪些 HTTP 行为，--db 参数在代码中有什么作用，以及哪些结论目前只能推断而没有实际运行验证。若阅读需求文档，将文档要求与源码已实现的行为分开，不能把需求当成实现。列明本次实际工具操作和尚未执行的验证建议。不要修改文件。'
for cid,names in [('code_only',['server.py']),('code_and_requirements',['server.py','README.md'])]:
 request='阅读以下文件：'+ '、'.join(names)+'。'+core
 c=dict(id=cid,request=request,files={name:v.file_digest(Q/'fixtures/api_bug'/name) for name in names});reg['cases'].append(c)
 old=v.load_contract(R/'data/experiments/RWKV_FACT_FIDELITY_FOCUSED_R1_20260913/contracts/api_bug.json');old.update(task_id=cid,user_request=request,execution_identity=reg['execution_identity'])
 facts=[('http','实际实现了哪些 HTTP 行为','明确GET /health返回200与ok:true、其他GET501；不虚构POST/业务路由已实现'),('db','--db 参数在代码中有什么作用','--db必填解析但后续未使用；代码没有SQLite连接或业务持久化；不能因此宣称启动必报错'),('sources','列明本次实际工具操作和尚未执行的验证建议','如实报告本次读取等操作，将源码推断、文档需求和未执行的测试区分；有合理针对实现的验证建议')]
 old['requirements']=[dict(id=i,user_quote=q,outcome=o,level='essential',missing_effect='明确核心问题未回答',acceptance=o+'；允许等义表述，不限工具顺序',omission_policy='常规实现细节允许省略') for i,q,o in facts]
 v.freeze_contract(old,D/'contracts'/f'{cid}.json')
 for repeat in (1,2):
  p=D/'runs'/f'{cid}-focused-r{repeat}'/'workspace';p.mkdir(parents=True)
  for name in names:shutil.copyfile(Q/'fixtures/api_bug'/name,p/name)
for mode,repeat in reg['order']:
 cases=reg['cases'] if repeat==1 else list(reversed(reg['cases']))
 v.write_once(D/f'JOBS_{mode}_{repeat}.json',[dict(task_id=f'{c["id"]}-{mode}-r{repeat}',request=c['request'],workspace=str(D/'runs'/f'{c["id"]}-{mode}-r{repeat}'/'workspace'),output_dir=str(D/'runs'/f'{c["id"]}-{mode}-r{repeat}'/'execution'),max_calls=6,max_seconds=300,tool_scope='files') for c in cases])
v.write_once(D/'REGISTRATION.json',reg)
for rel in reg['source_pins']:
 dest=D/'source'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(R/rel,dest)
(D/'PLAN.zh-CN.md').write_text('两种来源条件×两遍：源码单独、相同源码加已有需求README；ABBA顺序，统一核心问题/模型/采样/zero/预算。输入文件列表随来源变化，不能声称任意输入因素的纯因果效应。实际读取暴露由真实trace核验；若模型没读新增文档则不能归因于它。外部评分提前冻结，不提供参考答案。仅复用获准真实原文，不训练、不新建数据集。数字问题已有原值正确而关系失真的证据，本轮进一步定位共同的事实来源对应问题。\n')
print(v.file_digest(D/'REGISTRATION.json'))
