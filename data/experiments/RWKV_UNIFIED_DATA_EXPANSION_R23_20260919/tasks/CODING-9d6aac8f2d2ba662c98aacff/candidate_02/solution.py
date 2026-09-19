import sys
v=sys.stdin.read().split();n=int(v[0]);k=int(v[1]);s=v[2];longest=max(map(len,s.replace('?', 'Y').split('Y')))
ok=False
if longest<=k:
 if k==0:ok=True
 else:
  for l in range(n-k+1):
   r=l+k
   if 'Y' not in s[l:r] and (l==0 or s[l-1]!='N') and (r==n or s[r]!='N'):ok=True;break
print('YES' if ok else 'NO')
