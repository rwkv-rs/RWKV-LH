import sys
v=sys.stdin.read().split();n,m,budget=map(int,v[:3]);budget=min(budget,n*m);global_dp=[0]+[-10**9]*budget
for row in v[3:3+n]:
 pref=[0]
 for c in row:pref.append(pref[-1]+int(c))
 old=[-10**9]*(m+1);old[0]=0;best=[0]
 for k in range(1,min(m,budget)+1):
  cur=[-10**9]*(m+1)
  for j in range(k,m+1):
   cur[j]=max(old[t]+max(pref[j]-pref[t],j-t-pref[j]+pref[t]) for t in range(k-1,j))
  best.append(cur[m]);old=cur
 new=[-10**9]*(budget+1)
 for used,x in enumerate(global_dp):
  if x<0:continue
  for k,score in enumerate(best[:budget-used+1]):new[used+k]=max(new[used+k],x+score)
 global_dp=new
print(max(global_dp))
