import sys
v=iter(map(int,sys.stdin.buffer.read().split()));n=next(v);goals=[0]+[next(v) for _ in range(n)];q=next(v);incoming=[0]*(n+1);milestones={};answer=sum(goals);out=[]
for _ in range(q):
 s=next(v);t=next(v);u=next(v);key=(s,t);old=milestones.pop(key,0)
 if old:
  if incoming[old]<=goals[old]:answer+=1
  incoming[old]-=1
 if u:
  if incoming[u]<goals[u]:answer-=1
  incoming[u]+=1;milestones[key]=u
 out.append(str(answer))
print('\n'.join(out))
