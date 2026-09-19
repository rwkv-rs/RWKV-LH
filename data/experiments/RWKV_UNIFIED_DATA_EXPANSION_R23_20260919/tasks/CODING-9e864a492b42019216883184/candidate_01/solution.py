import sys
v=list(map(int,sys.stdin.read().split()));n=v[0];a=v[1:];even=n//2-sum(x>0 and x%2==0 for x in a);odd=(n+1)//2-sum(x%2==1 for x in a);dp={(0,2):0};zeros=0
for x in a:
 nd={}
 for (used,last),cost in dp.items():
  for p in ([x%2] if x else [0,1]):
   e=used+(not x and p==0)
   if e>even or zeros+(x==0)-e>odd:continue
   key=(e,p);value=cost+(last!=2 and last!=p);nd[key]=min(nd.get(key,10**9),value)
 dp=nd;zeros+=(x==0)
print(min(dp.values()))
