"""Read frozen public call evidence; no retired protocol execution or model calls."""
from pathlib import Path
import collections,hashlib,json,re,subprocess
ROOT=Path('/home/chase/GitHub/RWKV-LH')
OUT=ROOT/'data/experiments/ARCHITECTURE_NECESSITY_REVIEW_R1_20260911'
OUT.mkdir(parents=True,exist_ok=True)
source=ROOT/'data/experiments/ROLE_INPUT_METHOD_REVIEW_R1_20260911/CALLS.json'
rows=json.loads(source.read_text())
groups=collections.defaultdict(list)
input_pins={}
for row in rows:
    if row['role']!='selector_intent': continue
    path=ROOT/row['input_path']; raw=path.read_bytes()
    digest=hashlib.sha256(raw).hexdigest(); assert digest==row['input_sha256']
    input_pins[row['input_path']]=digest
    text=raw.decode(); marker=re.search(r'SelectorIntentPromptV\d+: ',text)
    assert marker
    packet,_=json.JSONDecoder().raw_decode(text[marker.end():])
    groups[(row['task_id'],row['selection_id'])].append(dict(menu=row['menu'],selected=row['selected'],eligible=packet['eligible_labels'],tokens=row['input_tokens']))
boundaries=[]
for (task,boundary),lanes in groups.items():
    assert len(lanes)==3 and len({tuple(x['eligible']) for x in lanes})==1
    votes=[x['selected'] for x in lanes]
    boundaries.append(dict(task_id=task,selection_id=boundary,eligible_labels=lanes[0]['eligible'],votes=votes,
        only_one_eligible=len(lanes[0]['eligible'])==1,three_way_tie=len(set(votes))==3,
        input_tokens=sum(x['tokens'] for x in lanes)))
summary=dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    source_kind='historical frozen pre-repair calls, read-only counting; not a new evaluation',
    selector_boundaries=len(groups),selector_evaluations=sum(len(x) for x in groups.values()),
    cardinality_histogram=dict(sorted(collections.Counter(len(x['eligible_labels']) for x in boundaries).items())),
    singleton_boundaries=sum(x['only_one_eligible'] for x in boundaries),
    singleton_evaluations=3*sum(x['only_one_eligible'] for x in boundaries),
    three_way_ties=sum(x['three_way_tie'] for x in boundaries),
    new_model_calls=0,scoring_changed=False,training=False)
(OUT/'SELECTOR_BOUNDARIES.json').write_text(json.dumps(boundaries,ensure_ascii=False,indent=2)+'\n')
(OUT/'SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
(OUT/'INPUT_PINS.json').write_text(json.dumps(dict(source=str(source.relative_to(ROOT)),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),inputs=input_pins),indent=2)+'\n')
print(json.dumps(summary,ensure_ascii=False,indent=2))
