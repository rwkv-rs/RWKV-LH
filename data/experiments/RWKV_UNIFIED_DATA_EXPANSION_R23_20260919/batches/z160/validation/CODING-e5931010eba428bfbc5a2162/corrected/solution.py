import sys
v=list(map(int,sys.stdin.buffer.read().split()));n,m=v[:2];a=[v[2+i*n:2+(i+1)*n] for i in range(n)]
if m==1:
 print('\n'.join(' '.join(map(str,row)) for row in a));raise SystemExit
bits=max(v[2:],default=0).bit_length();rows=[[0]*n for _ in range(bits)];cols=[[0]*n for _ in range(bits)];one=[1<<i for i in range(n)]
for i in range(n):
 for j,value in enumerate(a[i]):
  while value:
   low=value&-value;b=low.bit_length()-1;rows[b][i]|=one[j];cols[b][j]|=one[i];value-=low
full=(1<<n)-1;answer=[[0]*n for _ in range(n)]
for b in range(bits):
 groups={}
 for j,column in enumerate(cols[b]):groups[column]=groups.get(column,0)|one[j]
 states=list({full}|{full^mask for mask in groups.values()});index={state:i for i,state in enumerate(states)};transition=[index[full^groups.get(state,0)] for state in states];current=[index[full^groups.get(row,0)] for row in rows[b]];remaining=m-2
 while remaining:
  if remaining&1:current=[transition[i] for i in current]
  remaining>>=1
  if remaining:transition=[transition[i] for i in transition]
 value=1<<b
 for i,state in enumerate(current):
  mask=states[state]
  while mask:
   low=mask&-mask;j=low.bit_length()-1;answer[i][j]|=value;mask-=low
print('\n'.join(' '.join(map(str,row)) for row in answer))
