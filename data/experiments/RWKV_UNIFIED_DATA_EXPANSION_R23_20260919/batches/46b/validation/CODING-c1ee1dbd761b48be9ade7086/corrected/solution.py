import sys
from array import array
lines=sys.stdin.buffer.readlines();code={65:0,84:1,71:2,67:3};s=[code[x] for x in lines[0].strip()];n=len(s);trees=[None]
for m in range(1,11):
 part=[]
 for r in range(m):
  length=(n-1-r)//m+1;group=[array('i',[0])*(length+1) for _ in range(4)]
  for j in range(length):group[s[r+j*m]][j+1]=1
  for bit in group:
   for j in range(1,length+1):
    p=j+(j&-j)
    if p<=length:bit[p]+=bit[j]
  part.append(group)
 trees.append(part)
def prefix(bit,j):
 answer=0
 while j:answer+=bit[j];j-=j&-j
 return answer
out=[]
for line in lines[2:]:
 v=line.split()
 if not v:continue
 if v[0]==b'1':
  x=int(v[1])-1;c=code[v[2][0]];old=s[x]
  if c==old:continue
  for m in range(1,11):
   group=trees[m][x%m];j=x//m+1
   while j<len(group[0]):group[old][j]-=1;group[c][j]+=1;j+=j&-j
  s[x]=c
 else:
  l=int(v[1])-1;r=int(v[2])-1;e=v[3];m=len(e);answer=0
  for j,c in enumerate(e):
   pos=l+j
   if pos>r:break
   residue=pos%m;bit=trees[m][residue][code[c]];answer+=prefix(bit,(r-residue)//m+1)-prefix(bit,pos//m)
  out.append(str(answer))
print('\n'.join(out))
