from pathlib import Path
import hashlib,json
R=Path('/home/chase/GitHub/RWKV-LH'); O=R/'data/experiments/SELECTOR_SEMANTIC_REVIEW_R1_20260910'; W=R/'data/experiments/SELECTOR_WAIVER_RENEWAL_R1_20260910'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
wrapper='''"""Exact 14-source waiver scope, augmented only by two independently reviewed labels."""
from pathlib import Path
import hashlib,json,subprocess,sys
ROOT=Path('/home/chase/GitHub/RWKV-LH')
OUT=ROOT/'data/experiments/SELECTOR_SEMANTIC_REVIEW_R1_20260910'
W=ROOT/'data/experiments/SELECTOR_WAIVER_RENEWAL_R1_20260910'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def require(ok,msg):
 if not ok: raise SystemExit(msg)
require(len(sys.argv)==1,'No caller selectable scope')
p=json.loads((OUT/'SCOPE_ADDENDUM_PROPOSAL.json').read_text())
for key in ('base_registration','reviewed_registration','waiver','dispositions','decision_one','decision_two'):
 item=p[key]; require(sha(Path(item['path']))==item['sha256'],'Pinned bytes changed: '+key)
base=json.loads(Path(p['base_registration']['path']).read_text())
reviewed=json.loads(Path(p['reviewed_registration']['path']).read_text())
stripped=json.loads(json.dumps(reviewed))
for record in stripped['source_runs']: record['artifacts'].pop('human_reviews',None)
require(stripped==base,'Only human_reviews additions allowed')
require(len(base['source_runs'])==14,'14-source scope')
for record in reviewed['source_runs']:
 item=record['artifacts'].get('human_reviews')
 if item: require(sha(Path(item['path']))==item['sha256'],'Human review bytes changed')
for suffix,who in [('ONE','one'),('TWO','two')]:
 a=json.loads((OUT/('SCOPE_ADDENDUM_APPROVAL_'+suffix+'.json')).read_text())
 require(a['decision']=='accept' and a['reviewer']=='AI reviewer /root/waiver_review_'+who,'Independent accept missing')
 require(a['proposal_sha256']==sha(OUT/'SCOPE_ADDENDUM_PROPOSAL.json') and a['wrapper_sha256']==sha(Path(__file__)),'Exact approval mismatch')
cmd=[sys.executable,'-m','rwkv_lh.goal_state_protocols.role_trace_dataset_v1','extract','--registration',p['reviewed_registration']['path'],'--output',str(OUT/'reviewed_candidates'),'--role','selector_intent','--equivalence-waiver',p['waiver']['path'],'--waiver-sha256',p['waiver']['sha256']]
with (OUT/'REVIEWED_EXTRACTION.log').open('x') as log: result=subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
sys.exit(result.returncode)
'''
wp=O/'extract_reviewed_scoped_sources_20260910.py'; wp.write_text(wrapper)
p={'scope':'Same 14 production sources and same ten frozen/current file pairs; ONLY append pin-bound human_reviews. No source artifacts, scope, role, prompt, State, or score changes. Original signed wrapper and extraction remain immutable. This addendum is part of the same two-commit renewal, not global execution equivalence.','accepted_original':34,'accepted_correction':68,'rejected':24,'pending_dispositions':0,'rejection_policy':'No rejected row receives human_reviews. Raw extractor may still report those rows in review_queue; downstream rejection ledger closes review work, never converts rejected rows to admitted samples.','wrapper_sha256':sha(wp),'optimizer_steps':0}
for k,path in {'base_registration':W/'SCOPED_SOURCE_REGISTRATION.json','reviewed_registration':O/'REVIEWED_SOURCE_REGISTRATION.json','waiver':W/'SCOPED_EQUIVALENCE_WAIVER_ACCEPTED.json','dispositions':O/'FINAL_DISPOSITIONS.json','decision_one':O/'DECISIONS_ONE.json','decision_two':O/'DECISIONS_TWO.json'}.items(): p[k]={'path':str(path),'sha256':sha(path)}
(O/'SCOPE_ADDENDUM_PROPOSAL.json').write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n'); print(sha(O/'SCOPE_ADDENDUM_PROPOSAL.json'))
