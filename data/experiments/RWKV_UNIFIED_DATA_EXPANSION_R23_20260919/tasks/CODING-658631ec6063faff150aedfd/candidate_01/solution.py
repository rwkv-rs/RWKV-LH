import sys
v=sys.stdin.buffer.read().split();n,m=map(int,v[:2]);table=v[2:2+n];r,c=map(int,v[2+n:4+n]);pattern=v[4+n:];requirements={};bad=False
for i in range(r):
 for j,ch in enumerate(pattern[i]):
  if ch==63:continue
  key=i%n,j%m
  if key in requirements and requirements[key]!=ch:bad=True
  requirements[key]=ch
if bad:print('\n'.join(['0'*m]*n));raise SystemExit
masks=[];allbits=(1<<m)-1
for row in table:
 data={}
 for j,ch in enumerate(row):data[ch]=data.get(ch,0)|(1<<j)
 masks.append(data)
groups={}
for (i,j),ch in requirements.items():groups.setdefault(i,[]).append((j,ch))
ordered=sorted(groups.items(),key=lambda x:-len(x[1]));out=[]
for start in range(n):
 possible=allbits
 for offset,conditions in ordered:
  data=masks[(start+offset)%n]
  for shift,ch in conditions:
   mask=data.get(ch,0);possible&=((mask>>shift)|(mask<<(m-shift)))&allbits
   if not possible:break
  if not possible:break
 out.append(''.join('1' if possible>>j&1 else '0' for j in range(m)))
print('\n'.join(out))
