import sys
v=list(map(int,sys.stdin.buffer.read().split()));n,k,S=v[:3];a=v[3:3+n];pattern=v[3+n:];equal=[-1]*k;lower=[-1]*k;upper=[-1]*k;last=[-1]*(S+1)
for j,x in enumerate(pattern):
 equal[j]=last[x]
 if equal[j]<0:
  for y in range(x-1,0,-1):
   if last[y]>=0:lower[j]=last[y];break
  for y in range(x+1,S+1):
   if last[y]>=0:upper[j]=last[y];break
 last[x]=j
def fits(seq,pos,j):
 start=pos-j;x=seq[pos]
 if equal[j]>=0:return x==seq[start+equal[j]]
 return (lower[j]<0 or seq[start+lower[j]]<x) and (upper[j]<0 or x<seq[start+upper[j]])
pi=[0]*k;j=0
for i in range(1,k):
 while j and not fits(pattern,i,j):j=pi[j-1]
 if fits(pattern,i,j):j+=1
 pi[i]=j
out=[];j=0
for i in range(n):
 while j and not fits(a,i,j):j=pi[j-1]
 if fits(a,i,j):j+=1
 if j==k:out.append(i-k+2);j=pi[j-1]
print(len(out))
if out:print('\n'.join(map(str,out)))
