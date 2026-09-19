import sys,math
v=sys.stdin.read().split();s=v[0];budget=int(v[1]);n=len(s);letters='KEY';positions=[[i for i,c in enumerate(s) if c==letter] for letter in letters];totals=list(map(len,positions))
if budget>=n*(n-1)//2:
 answer=math.factorial(n)
 for total in totals:answer//=math.factorial(total)
 print(answer);raise SystemExit
before=[]
for p in range(n):before.append([sum(x<p for x in arr) for arr in positions])
dp={(0,0,0):{0:1}}
for step in range(n):
 new={}
 for used,counts in dp.items():
  for kind in range(3):
   if used[kind]==totals[kind]:continue
   p=positions[kind][used[kind]];cost=p-sum(min(used[j],before[p][j]) for j in range(3));key=list(used);key[kind]+=1;key=tuple(key);out=new.setdefault(key,{})
   for old,ways in counts.items():
    target=old+cost
    if target<=budget:out[target]=out.get(target,0)+ways
 dp=new
print(sum(dp.get(tuple(totals),{}).values()))
