import sys
P=998244353
v=iter(map(int,sys.stdin.buffer.read().split()));height=next(v);width=next(v);n=next(v);rows=[1]*height;cols=[1]*width
for _ in range(n):
 a=next(v)-1;b=next(v)-1;c=next(v)-1;d=next(v)-1;rows[a]=rows[c]=0;cols[b]=cols[d]=0
R=sum(rows);C=sum(cols)
def matching(line):
 previous=[1];current=[1]
 for i,free in enumerate(line):
  following=current[:]
  if i and free and line[i-1]:
   if len(following)<len(previous)+1:following.append(0)
   for j,x in enumerate(previous):following[j+1]=(following[j+1]+x)%P
  previous,current=current,following
 return current
vr=matching(rows);hc=matching(cols);limit=max(R,C);fact=[1]*(limit+1)
for i in range(1,limit+1):fact[i]=fact[i-1]*i%P
inv=[1]*(limit+1);inv[limit]=pow(fact[limit],P-2,P)
for i in range(limit,0,-1):inv[i-1]=inv[i]*i%P
answer=0
for vertical,ways in enumerate(vr):
 if vertical>C:break
 remaining_rows=R-2*vertical;factor=ways*fact[remaining_rows]%P
 for horizontal in range(min(len(hc)-1,remaining_rows,(C-vertical)//2)+1):
  remaining_cols=C-2*horizontal
  answer=(answer+factor*hc[horizontal]%P*inv[remaining_rows-horizontal]%P*fact[remaining_cols]%P*inv[remaining_cols-vertical])%P
print(answer)
