import sys
lines=sys.stdin.read().splitlines();out=[];at=0
while at<len(lines) and lines[at]!='#':
 plain,cipher,second=lines[at:at+3];at+=3;n=len(plain);chosen=None
 for k in range(1,n+1):
  adjacency=[]
  for j in range(k):
   allowed=[]
   for i in range(k):
    if all(plain[base+i]==cipher[base+j] for base in range(0,n,k) if base+i<n and base+j<n):allowed.append(i)
   adjacency.append(allowed)
  match=[-1]*k
  def augment(j,seen):
   for i in adjacency[j]:
    if seen[i]:continue
    seen[i]=True
    if match[i]<0 or augment(match[i],seen):match[i]=j;return True
   return False
  if all(augment(j,[False]*k) for j in range(k)):chosen=(k,match);break
 if chosen is None:out.append(second);continue
 k,match=chosen;decoded=[]
 for base in range(0,len(second),k):
  for i in range(k):
   pos=base+match[i];decoded.append(second[pos] if pos<len(second) else '?')
 out.append(''.join(decoded))
print('\n'.join(out))
