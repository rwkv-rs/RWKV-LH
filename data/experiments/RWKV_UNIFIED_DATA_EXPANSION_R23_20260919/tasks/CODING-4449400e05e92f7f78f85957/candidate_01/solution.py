import sys,bisect
v=list(map(int,sys.stdin.buffer.read().split()));n,m=v[:2];grass=v[2:2+n];hunger=[[] for _ in range(n+1)];total=[0]*(n+1)
for f in grass:total[f]+=1
for f,h in zip(v[n+2::2],v[n+3::2]):hunger[f].append(h)
for hs in hunger:hs.sort()
MOD=1000000007;left=[0]*(n+1);scores=[0]*(n+1);ways=[1]*(n+1);score=0;product=1
for f in range(1,n+1):
 r=bisect.bisect_right(hunger[f],total[f])
 if r:scores[f]=1;ways[f]=r;score+=1;product=product*r%MOD
best=score;answer=product
for f in grass:
 score-=scores[f];product=product*pow(ways[f],MOD-2,MOD)%MOD
 left[f]+=1;lc=left[f];rc=total[f]-lc;hs=hunger[f];l=bisect.bisect_right(hs,lc);r=bisect.bisect_right(hs,rc)
 # Count a chosen subset at its first feasible cut, when its final left endpoint appears.
 if l and hs[l-1]==lc:
  available=r-int(lc<=rc);value=score+1+int(available>0);count=product*max(1,available)%MOD
  if value>best:best=value;answer=count
  elif value==best:answer=(answer+count)%MOD
 pairs=l*r-min(l,r)
 if pairs:scores[f]=2;ways[f]=pairs
 elif l+r:scores[f]=1;ways[f]=l+r
 else:scores[f]=0;ways[f]=1
 score+=scores[f];product=product*ways[f]%MOD
print(best,answer)
