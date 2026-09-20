from pathlib import Path
import json,random,subprocess,itertools,functools
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_UNIFIED_DATA_EXPANSION_R23_20260919';paths={r['ordinal']:r['candidate_path'] for r in json.loads((D/'AUTHORED_BATCHz105.json').read_text())['candidates']};rng=random.Random(20260920)
def run(o,text):return int(subprocess.check_output([str(R/'.venv/bin/python'),paths[o]],input=text.encode(),timeout=20))
covers=[]
for y in range(3):
 for x in range(3):covers.append({y*4+x,y*4+x+1,y*4+x+4,y*4+x+5})
for trial in range(110):
 days=rng.randrange(1,10);schedule=[[rng.random()<0.16 for _ in range(16)] for _ in range(days)]
 @functools.lru_cache(None)
 def search(day,pos,ages):
  if day==days:return True
  for target in range(9):
   if day==0 and target!=4:continue
   if day and pos//3!=target//3 and pos%3!=target%3:continue
   if any(schedule[day][c] for c in covers[target]):continue
   nxt=tuple(0 if c in covers[target] else ages[c]+1 for c in range(16))
   if max(nxt)<=6 and search(day+1,target,nxt):return True
  return False
 expected=int(search(0,4,(0,)*16));text=str(days)+'\n'+''.join(' '.join(str(int(v)) for v in row)+'\n' for row in schedule)+'0\n';actual=run(548,text);assert actual==expected,(text,actual,expected)
assert run(548,'365\n'+('0 '*16+'\n')*365+'0\n')==1
for trial in range(130):
 n=rng.randrange(1,7);edges=[]
 for w in range(1,n):edges.append((rng.randrange(w),w,rng.randrange(1,15)))
 extra=[(a,b) for a in range(n) for b in range(a+1,n) if all((u,w)!=(a,b) for u,w,c in edges)];rng.shuffle(extra)
 for a,b in extra[:rng.randrange(min(4,len(extra))+1)]:edges.append((a,b,rng.randrange(1,15)))
 adj=[[] for _ in range(n)]
 for i,(a,b,c) in enumerate(edges):adj[a].append((b,c,i))
 paths_all=[]
 def paths(u,mask,cost):
  if mask:paths_all.append((mask,cost))
  for w,c,i in adj[u]:paths(w,mask|1<<i,cost+c)
 paths(0,0,0);full=(1<<len(edges))-1;dp=[10**9]*(full+1);dp[0]=0
 for mask in range(full+1):
  for covered,cost in paths_all:
   nxt=mask|covered
   if dp[mask]+cost<dp[nxt]:dp[nxt]=dp[mask]+cost
 text=str(n)+'\n'+''.join(str(len(row))+' '+ ' '.join(f'{w+1} {c}' for w,c,i in row)+'\n' for row in adj);actual=run(581,text);assert actual==dp[full],(text,actual,dp[full])
(D/'PUBLIC_CROSSCHECKS_BATCHz105.json').write_text(json.dumps({'status':'passed','cases':{'548':111,'581':130},'seed':20260920,'private_cases_read':False,'oracles':{'548':'Full sixteen-field drought state search, plus full-year feasible instance','581':'Enumerate every start-rooted game session and exact bitmask minimum-cost story-edge cover'}},indent=2)+'\n');print('public passed')
