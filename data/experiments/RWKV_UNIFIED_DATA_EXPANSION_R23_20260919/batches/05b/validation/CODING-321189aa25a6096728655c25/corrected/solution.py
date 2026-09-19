import sys
v=sys.stdin.buffer.read().split();n=int(v[0]);s=v[1];q=int(v[2]);queries=[(int(v[3+2*i]),v[4+2*i][0]) for i in range(q)];tables={}
for c in {c for m,c in queries}:
 best=[0]*(n+1)
 if c not in s:tables[c]=list(range(n+1));continue
 for left in range(n):
  wrong=0
  for right in range(left,n):
   wrong+=s[right]!=c;length=right-left+1
   if length>best[wrong]:best[wrong]=length
 for i in range(1,n+1):best[i]=max(best[i],best[i-1])
 tables[c]=best
print('\n'.join(str(tables[c][m]) for m,c in queries))
