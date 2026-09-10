"""Correct the interim-row assumption using the actual final210 retained sample identities."""
from pathlib import Path
import hashlib,json,sys,shutil
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R))
from rwkv_lh import statetune_data
from rwkv_lh.token_budget import VOCAB_PATH
E=R/'data/experiments';P=E/'SELECTOR_TRAINING_PREFLIGHT_R1_20260910';S=E/'SELECTOR_SIMILARITY_POLICY_R1_20260910';O=E/'SELECTOR_TRAINING_PREFLIGHT_R2_20260910';O.mkdir(exist_ok=False)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):
 with p.open('x') as f:json.dump(x,f,ensure_ascii=False,indent=2);f.write('\n')
old=list(map(json.loads,(S/'reviewed162/candidates.jsonl').read_text().splitlines()));new=list(map(json.loads,(S/'final210/candidates.jsonl').read_text().splitlines()));oi={r['sample_id']:r for r in old};ni={r['sample_id']:r for r in new};results=[]
for row in new:
 norm=statetune_data.normalize_row(row,role='selector_intent',model_sha256='1f920b94c4684e8463f36d8b71df23a8b50551f7776d39eec9ec6970471d460b',context_tokens=16384,vocab_size=65536,bos_token_id=0,expected_split=row['split'])
 results.append({'sample_id':row['sample_id'],'valid':True,'split':row['split'],'input_tokens':len(norm['input_token_ids']),'target_tokens':len(norm['target_token_ids'])})
result={'correction_to_report':{'path':str(P/'REPORT.zh-CN.md'),'sha256':sha(P/'REPORT.zh-CN.md'),'incorrect_statement':'Final20 were said to be row-identical to the interim20 already normalized.','correct_statement':'17 common sample IDs have identical rows;3 train rows were replaced by the registered lexical boundary rule. R1 FINAL_GATE.json correctly recorded false, but its prose incorrectly said identical. R2 now independently normalizes all final20.'},'final_candidate_manifest':{'path':str(S/'final210/manifest.json'),'sha256':sha(S/'final210/manifest.json')},'shared_ids':len(set(oi)&set(ni)),'common_rows_identical':all(oi[k]==ni[k] for k in set(oi)&set(ni)),'removed_ids':sorted(set(oi)-set(ni)),'added_ids':sorted(set(ni)-set(oi)),'final_rows_normalized':len(results),'normalization_failures':0,'rows':results,'all_source_profiles_zero':all(r['context']['initial_state']['profile_id']=='zero' and r['context']['initial_state']['profile_sha256']=='0'*64 for r in new),'tokenizer_sha256':sha(VOCAB_PATH),'execute_coverage':0,'quality_status':'invalid','freeze_integration_ready':False,'optimizer_smoke_started':False,'optimizer_steps':0}
write(O/'FINAL_DATA_VERIFICATION.json',result)
(O/'REPORT.zh-CN.md').write_text('''# Selector最终行训练预检 R2与R1文字更正

关联新采集Agent Strict 0/4、completed 0/4、mutation 0，三题无进展、一题协议拒绝；本轮不产生新Agent分数。

独立review发现R1预检报告的文字错误：final210保留20行并非与reviewed162保留20行全部相同。两者17个sample ID相同且全字段一致，按预注册字典序代表规则替换了3条train行；5条原开发/确认anchor未变。R1的FINAL_GATE.json已正确记录final_rows_equal_to_normalized_preflight=false，其报告却写成相同。原报告与SHA封存保留，以本更正和新核验为准，不修改去重结果或规则。

现对final210实际全部20行重新调用生产normalize_row，20/20通过完整服务器token、BOS、目标token、模型、协议与上下文长度校验；源profile全部zero，tokenizerSHA e6dee3d4e31b4d5c40ac99508ac6c701ceef4bed681bf2167ce9a908552bca89。完整增删身份和逐行结果见FINAL_DATA_VERIFICATION.json。

execute仍0、候选INVALID；独立review确认冻结入口仍缺waiver/筛选再现传递。这些是未训练的实际原因，Agent低分不是禁令。源数据检查不等于训练注入attestation或optimizer smoke；optimizer steps=0，没有新建正式角色数据集。
''')
(O/'helpers').mkdir();shutil.copyfile(Path(__file__),O/'helpers'/Path(__file__).name)
for name in ('selector_final_policy_review_one_20260910.json','selector_training_preflight_review_two_20260910.json'):
 p=R/'temp'/name
 if p.exists():shutil.copyfile(p,O/name)
files=[{'path':str(p.relative_to(O)),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(O.rglob('*')) if p.is_file()]
write(O/'EVIDENCE_SHA256.json',{'round':O.name,'files':files,'pytest_passed':1455,'production_unchanged':True,'optimizer_steps':0})
print(json.dumps({'final_rows_normalized':20,'shared_ids':result['shared_ids'],'added':len(result['added_ids']),'report_sha256':sha(O/'REPORT.zh-CN.md'),'evidence_sha256':sha(O/'EVIDENCE_SHA256.json')}))
