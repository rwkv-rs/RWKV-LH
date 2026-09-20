import sys
v=list(map(int,sys.stdin.buffer.read().split()));n,k=v[:2];adj=[[] for _ in range(n)];total=0
for i in range(2,len(v),3):
 a,b,w=v[i:i+3];a-=1;b-=1;adj[a].append((b,w));adj[b].append((a,w));total+=w
parent=[-1]*n;children=[[] for _ in range(n)];order=[0]
for u in order:
 for w,c in adj[u]:
  if w!=parent[u]:parent[w]=u;children[u].append((w,c));order.append(w)
order.reverse()
def feasible(bound):
 near=[0]*n;count=[0]*n
 for u in order:
  distances=[];number=0
  for w,c in children[u]:distances.append(near[w]+c);number+=count[w]
  if not distances:count[u]=1;continue
  distances.sort();j=0
  while j+1<len(distances) and distances[j]+distances[j+1]<bound:j+=1;number-=1
  nearest=distances[j]
  if nearest>=bound:nearest=0;number+=1
  near[u]=nearest;count[u]=number
 return count[0]>=k
low=0;high=total+1
while low+1<high:
 mid=(low+high)//2
 if feasible(mid):low=mid
 else:high=mid
print(low)
