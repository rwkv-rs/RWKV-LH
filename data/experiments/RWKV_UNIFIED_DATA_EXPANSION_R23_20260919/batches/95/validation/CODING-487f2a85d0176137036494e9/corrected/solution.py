import sys,heapq
v=sys.stdin.buffer.read().split();p=0;out=[]
while p<len(v):
 n=int(v[p]);p+=1
 if n==0:break
 words=v[p:p+n];p+=n;distance={};queue=[]
 for a in words:
  for b in words:
   if a!=b and b.startswith(a):
    suffix=b[len(a):];cost=len(b)
    if cost<distance.get(suffix,10**30):distance[suffix]=cost;heapq.heappush(queue,(cost,suffix))
 answer=-1
 while queue:
  cost,suffix=heapq.heappop(queue)
  if distance[suffix]!=cost:continue
  if not suffix:answer=cost;break
  for word in words:
   if suffix.startswith(word):rest=suffix[len(word):];value=cost
   elif word.startswith(suffix):rest=word[len(suffix):];value=cost+len(rest)
   else:continue
   if value<distance.get(rest,10**30):distance[rest]=value;heapq.heappush(queue,(value,rest))
 out.append(str(answer))
print('\n'.join(out))
