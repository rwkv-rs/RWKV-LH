from pathlib import Path
import json, shutil, sys
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R))
from rwkv_lh import task_review as v
from rwkv_lh.model import LongHorizonModel
D=R/'data/experiments/RWKV_DOCUMENT_QA_AND_BUGCHECK_R1_20260913'
B=json.loads((R/'data/experiments/RWKV_FEEDBACK_TASK_BASELINE_R1_20260913/REGISTRATION.json').read_text())
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
cases=[
('rag_overview',Path('/home/chase/GitHub/rwkvrag'),['README.md'],'阅读 README.md，回答本项目使用什么模型和检索方式，现有实验能说明什么、不能说明什么。只依据文件回答。', [('stack','使用什么模型和检索方式','RWKV 2.9B、OpenSearch BM25、不使用embedding'),('limits','现有实验能说明什么、不能说明什么','固定Reader/Writer实验有改善，但Planner与复杂问题/证据引用仍不可靠，不能推广为全场景准确率；具体分数可省略')]),
('rag_rules',Path('/home/chase/GitHub/rwkvrag/llamaindex-retrieval'),['ARCHITECTURE_RULES.md'],'阅读 ARCHITECTURE_RULES.md，说明文本证据如何成为回答材料，模型与程序各负责什么，以及原始答案和来源记录有哪些约束。只依据文件回答。',[('material','文本证据如何成为回答材料','Writer仅看Resolver选中的逐字证据；正文切片保留overlap和原子结构/父级上下文'),('roles','模型与程序各负责什么','模型语义决定；程序传输切分检索排序去重解析校验'),('audit','原始答案和来源记录有哪些约束','原始回答不可改写/兜底；调用保留prompt、输出和证据ID等可追溯记录；无需列齐所有字段')]),
('api_bug',R/B['cases'][0]['workspace_source'],['server.py','README.md'],'检查 server.py 与 README.md 的实现差距，找出一个影响用户使用的真实缺陷。说明代码位置、触发条件、实际后果和可复核的验证方法；区分已运行的验证与建议。不要修改文件。',[('bug','真实缺陷','指出至少一个代码支持的契约缺失：例如--db未使用/持久化缺失，或业务接口尚未实现；接受其他有证据可复现缺陷，不强制参考路径'),('evidence','代码位置、触发条件、实际后果和可复核的验证方法','给出定位及具体触发与后果、可执行的验证步骤；未运行时不能宣称验证通过')]),
('backup_check',R/B['cases'][2]['workspace_source'],['config_store/sqlite_io.py'],'检查 config_store/sqlite_io.py 中创建备份的实现：目标文件已存在时是否会被覆盖？给出代码依据和验证方法。如果未发现这个问题，明确说明，不要为了报告bug而编造。不要修改文件。',[('behavior','目标文件已存在时是否会被覆盖','os.link排他创建，已存在则失败且不覆盖；finally清理暂存文件'),('proof','代码依据和验证方法','定位write_backup_exclusive与os.link，给出已有目标内容保持不变及异常的验证思路；不虚称已执行')])]
source={str(p.relative_to(R)):v.file_digest(p) for p in sorted((R/'rwkv_lh').rglob('*.py'))}
source['scripts/run_rwkv_read_only_agent.py']=v.file_digest(R/'scripts/run_rwkv_read_only_agent.py')
identity=dict(json.loads((R/'data/experiments/RWKV_FEEDBACK_TASK_BASELINE_R1_20260913/contracts/health.json').read_text())['contract']['execution_identity'])
identity['source']=v.digest(source)
identity['budget']=v.digest({'max_calls':6,'max_seconds':300,'output_tokens':1800})
reg={'round':D.name,'source_pins':source,'execution_identity':identity,'sampling':LongHorizonModel._SAMPLING.to_dict(),'model_name':B['model_name'],'model_sha256':B['model_sha256'],'base_url':B['base_url'],'state':'fresh zero per task, continuous native observation State within task','budget':{'max_calls':6,'max_seconds':300,'output_tokens':1800,'total_tasks':16,'total_calls_max':96,'total_task_seconds_max':4800},'order':[['serial',1],['parallel',1],['parallel',2],['serial',2]],'quality_rule':'all essentials; details optional, fact fidelity; no fixed tool path; minor extra-detail defect reported separately; major unsupported claim fails','gate':'each mode two consecutive repeats all4 met; zero illegal calls and false completion for stability, not general reliability','performance':'report delivery first, all failed attempts charged; throughput accepted tasks / batch elapsed; no resource or cost improvement claim when quality differs or prices/peak unknown','cases':[]}
(D/'contracts').mkdir();(D/'fixtures').mkdir()
for cid,root,paths,request,requirements in cases:
    dest=D/'fixtures'/cid;dest.mkdir()
    pins={}
    for rel in paths:
        target=dest/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(root/rel,target);pins[rel]=v.file_digest(target)
    contract={'schema':v.CONTRACT_SCHEMA,'task_id':cid,'user_request':request,'kind':'task_trial','protocol_error_policy':'feedback','execution_identity':identity,'requirements':[{'id':rid,'user_quote':quote,'outcome':out,'level':'essential','missing_effect':'用户问题未得到实质回答','acceptance':out+'；允许等义表达，不限制工具路径','omission_policy':'未明确要求的语法、行号和一般细节允许省略'} for rid,quote,out in requirements]}
    v.freeze_contract(contract,D/'contracts'/f'{cid}.json')
    reg['cases'].append({'id':cid,'request':request,'source_root':str(root),'files':pins})
save(D/'REGISTRATION.json',reg)
for mode,repeat in reg['order']:
    jobs=[]
    for c in reg['cases']:
        rid=f'{c["id"]}-{mode}-r{repeat}';p=D/'runs'/rid;p.mkdir(parents=True)
        shutil.copytree(D/'fixtures'/c['id'],p/'workspace')
        jobs.append({'task_id':rid,'request':c['request'],'workspace':str(p/'workspace'),'output_dir':str(p/'execution'),'max_calls':6,'max_seconds':300})
    save(D/f'JOBS_{mode}_{repeat}.json',jobs)
print(v.file_digest(D/'REGISTRATION.json'))
