import sys
it=iter(map(int,sys.stdin.buffer.read().split()));n=next(it);events=[]
for _ in range(n):
 count=next(it);p=[(next(it),next(it)) for _ in range(count)];area=sum(p[i][0]*p[(i+1)%count][1]-p[i][1]*p[(i+1)%count][0] for i in range(count));orientation=1 if area>0 else -1
 for i in range(count):
  x,y=p[i];u,v=p[(i+1)%count]
  if x==u:events.append((x,min(y,v),max(y,v),-orientation*(1 if v>y else -1)))
events.sort();q=next(it);queries=sorted((next(it),next(it),i) for i in range(q));size=100002;bit=[0]*(size+1);answer=[0]*q;pos=0
def add(y,value):
 y+=1
 while y<=size:bit[y]+=value;y+=y&-y
for x,y,i in queries:
 while pos<len(events) and events[pos][0]<=x:
  _,low,high,value=events[pos];add(low,value);add(high,-value);pos+=1
 y+=1;total=0
 while y:total+=bit[y];y-=y&-y
 answer[i]=total
print('\n'.join(map(str,answer)))
