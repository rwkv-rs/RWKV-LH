from pathlib import Path
import sys,json,shutil
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R))
from rwkv_lh import task_review as v
Q=R/'data/experiments/RWKV_DOCUMENT_QA_AND_BUGCHECK_R1_20260913';D=R/'data/experiments/RWKV_FACT_FIDELITY_FOCUSED_R1_20260913';D.mkdir()
reg=json.loads((Q/'file_scope_probe/REGISTRATION.json').read_text());reg['round']=D.name
reg['question']='Focused user requests on existing real sources: numeric identity and file-described versus actually executed verification. Diagnostic, not a repair benefit or general capability claim.'
requests={
'rag_overview':'阅读 README.md，准确说明文中 Reader 和 Writer 的实验结果。区分模型或候选标签、实验分数、分子与分母；保留原文中的数字及其对应对象，不推算文件没有报告的成绩。再说明这些数字可以支持和不能支持的结论。只依据文件回答。',
'api_bug':'阅读 server.py 和 README.md，指出一个真实实现缺陷，并分别说明：文件或代码中描述的行为、本次你实际执行过的工具操作与得到的结果、尚未执行的建议验证步骤。没有执行过的测试明确写为未运行，不把代码推断或建议步骤说成实测结果。不要修改文件。'}
reg['cases']=[c for c in reg['cases'] if c['id'] in requests]
source={str(p.relative_to(R)):v.file_digest(p) for p in sorted((R/'rwkv_lh').rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
source['scripts/run_rwkv_read_only_agent.py']=v.file_digest(R/'scripts/run_rwkv_read_only_agent.py')
reg['source_pins']=source;reg['execution_identity']['source']=v.digest(source)
reg['budget']={'max_calls':6,'max_seconds':300,'output_tokens':1800,'total_tasks':4,'total_calls_max':24,'total_task_seconds_max':1200};reg['execution_identity']['budget']=v.digest(reg['budget'])
reg['order']=[['focused',1],['focused',2]];reg['gate']='Both existing-source tasks met in two consecutive repeats, zero illegal parameters and false work claims. Passing proves only focused requests within these files; prior broad-task and reading regression gates remain separate.'
reg['comparison_limit']='User question changed to localize a known failure, not production prompt fix; do not combine with or rescore old outcomes. Only negative executed-test boundary is tested; no successful execution observation injected.'
for c in reg['cases']:
 c['request']=requests[c['id']]
 old=v.load_contract(Q/'file_scope_probe/contracts'/f'{c["id"]}.json');old['user_request']=c['request'];old['execution_identity']=reg['execution_identity']
 if c['id']=='rag_overview':
  outcomes=[('numbers','区分模型或候选标签、实验分数、分子与分母','Reader48/60到60/60；Writer300是候选标签，固定36题17/36，zero10/36；不把300/1400等作为成绩分母'),('limits','可以支持和不能支持的结论','受控组结果及扩大1400条未继续提升；不冒称全场景准确率或能力上限')]
 else:outcomes=[('bug','指出一个真实实现缺陷','接受缺失业务接口、--db未使用或其他源码支持的真实缺陷，代码推断与实际HTTP观察明确区分'),('provenance','本次你实际执行过的工具操作','正确报告本次实际读取等工具；没有HTTP执行则明确未运行；文件描述、推断、建议与实际执行不混淆'),('verification','尚未执行的建议验证步骤','给出针对真实缺陷可复核的验证方法，准确标为建议，允许不同工具和表达')]
 old['requirements']=[dict(id=i,user_quote=q,outcome=o,level='essential',missing_effect='明确询问的核心信息未回答',acceptance=o+'；允许等义表达，不限执行路径',omission_policy='未要求的一般实现细节允许省略') for i,q,o in outcomes]
 v.freeze_contract(old,D/'contracts'/f'{c["id"]}.json')
 for repeat in (1,2):
  p=D/'runs'/f'{c["id"]}-focused-r{repeat}';p.mkdir(parents=True);shutil.copytree(Q/'fixtures'/c['id'],p/'workspace')
for mode,repeat in reg['order']:
 v.write_once(D/f'JOBS_{mode}_{repeat}.json',[dict(task_id=f'{c["id"]}-{mode}-r{repeat}',request=c['request'],workspace=str(D/'runs'/f'{c["id"]}-{mode}-r{repeat}'/'workspace'),output_dir=str(D/'runs'/f'{c["id"]}-{mode}-r{repeat}'/'execution'),max_calls=6,max_seconds=300,tool_scope='files') for c in reg['cases']])
v.write_once(D/'REGISTRATION.json',reg)
for rel in source:
 dest=D/'source'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(R/rel,dest)
(D/'PLAN.zh-CN.md').write_text('本轮只定位数字引用与执行来源区分。复用获准原文，不新建数据集；任务文本已聚焦，不能作为提示修复收益。两题两遍zero独立State，生产只读入口，六调用/300秒/1800输出。未强制读取顺序。评分只在外部。保留所有输出及精确token/State。当前不包含真实HTTP执行的阳性观察，不能证明全面来源区分。\n')
print(v.file_digest(D/'REGISTRATION.json'))
