from pathlib import Path
import hashlib,json,sys,collections
ROOT=Path('/home/chase/GitHub/RWKV-LH'); sys.path.insert(0,'/home/chase/GitHub/RWKV-LH-selector-500-r1-20260911')
from rwkv_lh.goal_state_protocols import selector_intent_v6 as protocol
OUT=ROOT/'data/experiments/SELECTOR_500_REVIEW_BATCH02_20260911'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,obj):
 with p.open('x') as f: json.dump(obj,f,ensure_ascii=False,indent=2); f.write('\n')
m=json.loads((OUT/'MANIFEST.json').read_text()); src=Path(m['source_path'])
if sha(src)!=m['source_sha256']: raise SystemExit('source mismatch')
rows=[json.loads(x) for x in src.read_text().splitlines()]; originals={r['sample_id']:r for r in rows}
reviews=[]
for suffix in ('ONE','TWO'):
 d=json.loads((OUT/f'DECISIONS_{suffix}.json').read_text())
 if d['manifest_sha256']!=sha(OUT/'MANIFEST.json') or d['source_sha256']!=sha(src): raise SystemExit('review manifest mismatch')
 indexed={x['sample_id']:x for x in d['decisions']}
 if len(indexed)!=len(originals) or set(indexed)!=set(originals): raise SystemExit('review coverage mismatch')
 if d['reviewer'] != 'AI reviewer /root/waiver_review_' + ('one' if suffix=='ONE' else 'two'): raise SystemExit('reviewer identity mismatch')
 reviews.append((d['reviewer'],indexed))
packets={p['packet_id']:p for p in m['packets']}; ledger=[]; attached=collections.defaultdict(list)
for row in rows:
 ds=[r[1][row['sample_id']] for r in reviews]; targets=[]
 for d in ds:
  if d['decision'] not in ('accept_original','accept_correction','reject'): raise SystemExit('unknown review decision')
  for key in ('request_id','original_output_record_sha256','run_id','boundary_event_id'):
   if d[key]!=row[key]: raise SystemExit('identity mismatch '+key)
  if d['input_sha256']!=hashlib.sha256(row['input_text'].encode()).hexdigest(): raise SystemExit('input mismatch')
  p=packets[d['packet_id']]
  if d['packet_sha256']!=p['sha256'] or sha(Path(p['path']))!=p['sha256']: raise SystemExit('packet mismatch')
  op=protocol.parse_target(row['original_target_text'])
  if d['original_operation']!=op or not set(d['evidence_refs'])<=set(row['available_evidence_refs']): raise SystemExit('label evidence mismatch')
  target=op if d['decision']=='accept_original' else d['suggested_operation'] if d['decision']=='accept_correction' else None
  if target is not None and target not in row['protocol_source']['eligible_labels']: raise SystemExit('ineligible correction')
  targets.append(target)
 accepted=targets[0] is not None and targets[0]==targets[1]
 rec={k:row[k] for k in ('sample_id','source_run_id','run_id','boundary_event_id','request_id','original_output_record_sha256')}
 rec.update(decision='accept' if accepted else 'reject',reviewer_decisions=[d['decision'] for d in ds],proposed_operations=targets,reason='two_independent_reviewers_agree' if accepted else 'reviewer_veto_or_disagreement')
 if accepted:
  target=protocol.TARGET_PREFIX+targets[0]
  if protocol.parse_target(target)!=targets[0]: raise SystemExit('canonical target mismatch')
  correction=target!=row['original_target_text']; rec.update(target_text=target,correction=correction)
  for (reviewer,_),d in zip(reviews,ds):
   record={k:row[k] for k in ('request_id','role','source_run_id','run_id','boundary_event_id','original_output_record_sha256')}
   record.update(input_sha256=d['input_sha256'],target_sha256=hashlib.sha256(target.encode()).hexdigest(),decision='accept',purpose='trace_correction' if correction else 'semantic_label',evidence_refs=d['evidence_refs'],rationale=d['rationale'],reviewer_id=reviewer)
   if correction: record['target_text']=target
   attached[(row['source_run_id'],row['run_id'])].append(record)
 ledger.append(rec)
write(OUT/'FINAL_DISPOSITIONS.json',{'manifest_sha256':sha(OUT/'MANIFEST.json'),'decision_shas':{s:sha(OUT/f'DECISIONS_{s}.json') for s in ('ONE','TWO')},'pending':0,'dispositions':ledger})
registration=json.loads((ROOT/'data/experiments/SELECTOR_500_BATCH02_20260911/FRESH_SOURCE_REGISTRATION.json').read_text())
for source in registration['source_runs']:
 key=(source['source_run_id'],source['run_id'])
 if key in attached:
  p=OUT/(source['run_id']+'.human_reviews.json'); write(p,attached[key]); source['artifacts']['human_reviews']={'path':str(p),'sha256':sha(p)}
write(OUT/'REVIEWED_SOURCE_REGISTRATION.json',registration)
summary={'reviewed':len(ledger),'pending':0,'accepted_original':sum(x['decision']=='accept' and not x['correction'] for x in ledger),'accepted_correction':sum(x.get('correction',False) for x in ledger),'rejected':sum(x['decision']=='reject' for x in ledger),'attached_review_records':sum(map(len,attached.values())),'registration_sha256':sha(OUT/'REVIEWED_SOURCE_REGISTRATION.json'),'source_scope_addendum_required':False,'optimizer_steps':0}
write(OUT/'RECONCILIATION.json',summary); print(json.dumps(summary))
