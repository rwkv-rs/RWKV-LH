from pathlib import Path
import sys,json,hashlib,concurrent.futures
R=Path('/home/chase/GitHub/RWKV-LH-teacher-budget-r19-20260916');sys.path.insert(0,str(R))
from rwkv_lh.strong_session import AuditedStrongClient
from rwkv_lh.supervisor_openai import SupervisorAPISettings
from rwkv_lh.correction_review import REVIEW_INSTRUCTION,REVIEW_SCHEMA,validate_review
D=Path('/home/chase/GitHub/RWKV-LH-coding-review-r20-20260917')
def run(p):
 packet=json.loads(p.read_text());dest=p.parent;events=[]
 def audit(e):
  events.append(e)
  with (dest/'QWEN_TRACE.jsonl').open('a') as f:f.write(json.dumps(e,ensure_ascii=False)+'\n')
 settings=SupervisorAPISettings(base_url='http://127.0.0.1:18244/v1',api_key='local',model='qwen3.8-27b-r17',stage_checker_model='qwen3.8-27b-r17',read_timeout_seconds=300,retry_attempts=1,semantic_repair_attempts=0,plan_cache_enabled=False,planner_request_options={'temperature':0,'thinking_token_budget':1024,'reasoning_effort':'medium','return_token_ids':True})
 c=AuditedStrongClient(settings,audit_hook=audit)
 try:
  raw=c._request_json(phase='state_tune_target_review',run_id=dest.name,request_digest=hashlib.sha256(p.read_bytes()).hexdigest(),system_prompt=REVIEW_INSTRUCTION,request_payload=packet,schema=REVIEW_SCHEMA,max_tokens=4096)
  (dest/'QWEN_RAW.json').write_text(json.dumps(raw,ensure_ascii=False,indent=2));v=validate_review(packet,raw);(dest/'QWEN_REVIEW.json').write_text(json.dumps(v,ensure_ascii=False,indent=2));print(dest.name,v['accepted'],flush=True)
 finally:c.close()
if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(2) as ex:list(ex.map(run,sorted(D.glob('*/PACKET.json'))))
