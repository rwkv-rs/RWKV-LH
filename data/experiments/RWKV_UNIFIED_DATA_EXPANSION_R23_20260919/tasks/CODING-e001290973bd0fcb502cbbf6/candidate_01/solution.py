import sys
v=list(map(int,sys.stdin.buffer.read().split()));n,m=v[:2];dp={(0,0):0}
for day in range(n):
 a,b,c=v[2+3*day:5+3*day];gain=[[c]*9 for _ in range(9)]
 for old in range(9):
  for new in range(9):
   best=c
   for low in range(old+1):
    for high in range(min(new,8-low)+1):
     if low+high:best=max(best,low*b+high*a)
   gain[old][new]=best
 updated={}
 for (used,old),value in dp.items():
  for new in range(min(8,m-used)+1):
   key=(used+new,new);score=value+gain[old][new]
   if score>updated.get(key,-10**30):updated[key]=score
 dp=updated
print(max(dp.values()))
