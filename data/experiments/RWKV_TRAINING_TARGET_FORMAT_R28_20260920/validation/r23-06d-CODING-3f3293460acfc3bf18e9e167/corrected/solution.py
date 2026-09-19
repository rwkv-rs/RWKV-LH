import sys
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];c=v[1:];answer=0
for i in range(0,n,2):
 balance=0;minimum=0
 for j in range(i+1,n,2):
  low=max(1,1-balance,-minimum);high=min(c[i],c[j]-balance)
  if high>=low:answer+=high-low+1
  balance-=c[j];minimum=min(minimum,balance)
  if j+1<n:balance+=c[j+1]
print(answer)
