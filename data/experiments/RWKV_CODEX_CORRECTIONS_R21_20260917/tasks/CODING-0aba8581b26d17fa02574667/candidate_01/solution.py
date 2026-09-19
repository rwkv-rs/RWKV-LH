import sys
from datetime import date,timedelta
v=sys.stdin.read().split();out=[]
for s in v[1:]:
 y,m,d=map(int,s.split(':'));day=date(y,m,d);par=d%2;elapsed=count=0
 while (day.day%2==par)==(elapsed%2==0):
  if elapsed%2==0:count+=1
  elapsed+=1;day+=timedelta(days=1)
 out.append(str(count))
print('\n'.join(out))
