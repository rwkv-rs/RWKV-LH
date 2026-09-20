import sys
v=list(map(int,sys.stdin.buffer.read().split()));n,k,m,a=v[:4];votes=[0]*n;last=[-1]*n
for time,c in enumerate(v[4:],1):votes[c-1]+=1;last[c-1]=time
remaining=m-a;answer=[]
for c in range(n):
 best=votes[c]+remaining;time=m if remaining else last[c];higher=sum(j!=c and (votes[j]>best or votes[j]==best and last[j]<time) for j in range(n))
 if best==0 or higher>=k:answer.append(3);continue
 if votes[c]==0:answer.append(2);continue
 costs=[]
 for j in range(n):
  if j==c:continue
  already=votes[j]>votes[c] or votes[j]==votes[c] and last[j]<last[c];costs.append(0 if already else votes[c]+1-votes[j])
 costs.sort();can_exclude=len(costs)>=k and sum(costs[:k])<=remaining;answer.append(2 if can_exclude else 1)
print(*answer)
