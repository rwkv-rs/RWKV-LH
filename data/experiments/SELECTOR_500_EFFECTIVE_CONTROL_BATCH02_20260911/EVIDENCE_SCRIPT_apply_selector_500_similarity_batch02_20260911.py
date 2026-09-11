"""Apply the immutable preregistration to admitted real-trace rows, preserving boundary units."""
from pathlib import Path
import argparse,collections,hashlib,json,sys
R=Path('/home/chase/GitHub/RWKV-LH'); sys.path.insert(0,'/home/chase/GitHub/RWKV-LH-selector-500-r1-20260911')
from rwkv_lh.role_trace_artifacts import _grams,_cosine_parts,build_artifacts,write_artifacts
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('bundles',nargs='+');a=p.parse_args()
O=R/'data/experiments/SELECTOR_500_SIMILARITY_BATCH02_20260911'; reg=json.loads((O/'PREREGISTRATION.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,obj):
 with p.open('x') as f:json.dump(obj,f,ensure_ascii=False,indent=2);f.write('\n')
if sha(Path(reg['input_anchor_path']))!=reg['input_anchor_sha256']:raise SystemExit('anchor changed')
anchors={r['sample_id']:r for r in map(json.loads,Path(reg['input_anchor_path']).read_text().splitlines()) if r['sample_id'] in reg['evaluation_anchor_sample_ids']}
rows=[];sources=[];inputs=[];requirements=None;scope=None
for path in a.bundles:
 b=Path(path);m=json.loads((b/'manifest.json').read_text());rs=list(map(json.loads,(b/'candidates.jsonl').read_text().splitlines()))
 if requirements is not None and requirements!=m['coverage_requirements']:raise SystemExit('coverage conditions differ')
 if scope is not None and scope!=m['provenance']['coverage_scope_sha256']:raise SystemExit('scope differs')
 requirements=m['coverage_requirements'];scope=m['provenance']['coverage_scope_sha256'];rows.extend(rs);sources.extend(m['provenance']['source_runs'])
 inputs.append({'path':str(b),'manifest_sha256':sha(b/'manifest.json'),'candidates_sha256':sha(b/'candidates.jsonl')})
byid={r['sample_id']:r for r in rows}
if len(byid)!=len(rows):raise SystemExit('duplicate sample')
if any(byid.get(k)!=r for k,r in anchors.items()):raise SystemExit('immutable anchor differs')
units=collections.defaultdict(list)
for r in rows:units[tuple(r[k] for k in ('source_run_id','run_id','boundary_event_id'))].append(r)
keys=sorted(units);parent=list(range(len(keys)))
def root(i):
 while i!=parent[i]:parent[i]=parent[parent[i]];i=parent[i]
 return i
gram={r['sample_id']:_grams(r['input_text']) for r in rows};edges=[]
for i,k in enumerate(keys):
 for j in range(i):
  hit=None
  for l in units[k]:
   for r in units[keys[j]]:
    if l['role']!=r['role']:continue
    dot,ls,rs=_cosine_parts(gram[l['sample_id']],gram[r['sample_id']])
    if (dot*dot*10000>=9025*ls*rs if ls and rs else l['input_text']==r['input_text']):hit=[l['sample_id'],r['sample_id']];break
   if hit:break
  if hit:parent[root(i)]=root(j);edges.append({'left_unit':i,'right_unit':j,'witness':hit})
components=collections.defaultdict(list)
for i in range(len(keys)):components[root(i)].append(i)
kept=[];excluded=[];details=[]
for number,indices in enumerate(sorted(components.values(),key=lambda ids:keys[min(ids)]),1):
 ids={r['sample_id'] for i in indices for r in units[keys[i]]};has_anchor=bool(ids&anchors.keys())
 train=[i for i in indices if all(r['split']=='train' for r in units[keys[i]])];winner=min(train,key=lambda i:keys[i]) if train and not has_anchor else None
 for i in indices:
  for r in units[keys[i]]:
   reason=None
   if r['split']!='train' and r['sample_id'] not in anchors:reason='not_an_immutable_evaluation_anchor'
   elif r['split']=='train' and has_anchor:reason='component_touches_immutable_evaluation_anchor'
   elif r['split']=='train' and i!=winner:reason='nonrepresentative_train_boundary'
   if reason:excluded.append({'sample_id':r['sample_id'],'source_run_id':r['source_run_id'],'run_id':r['run_id'],'boundary_event_id':r['boundary_event_id'],'input_sha256':hashlib.sha256(r['input_text'].encode()).hexdigest(),'component':number,'reason':reason})
   else:kept.append(r)
 details.append({'component':number,'units':[list(keys[i]) for i in indices],'anchor_ids':sorted(ids&anchors.keys()),'winner':list(keys[winner]) if winner is not None else None})
provenance={'requested_roles':['selector_intent'],'source_runs':sources,'coverage_scope_sha256':scope,'preregistration_sha256':sha(O/'PREREGISTRATION.json'),'inputs':inputs,'exclusion_ledger':a.name+'.EXCLUSIONS.json','recomputed_rows':len(rows)}
bundle=build_artifacts(kept,provenance=provenance,coverage_requirements=requirements)
write_artifacts(O/a.name,bundle)
write(O/(a.name+'.EXCLUSIONS.json'),{'policy_sha256':sha(O/'PREREGISTRATION.json'),'excluded':excluded,'components':details,'edges':edges})
summary={'input_rows':len(rows),'kept':len(kept),'excluded':len(excluded),'components':len(components),'anchors_unchanged':all(next(r for r in kept if r['sample_id']==k)==v for k,v in anchors.items()),'status':bundle.manifest['status'],'counts':bundle.manifest['counts_by_role'],'coverage':bundle.manifest['coverage_audit'],'gates':bundle.manifest['quality_gates'],'violations':len(bundle.manifest['similarity_audit']['violations']),'optimizer_steps':0}
write(O/(a.name+'.RESULT.json'),summary);print(json.dumps(summary))
