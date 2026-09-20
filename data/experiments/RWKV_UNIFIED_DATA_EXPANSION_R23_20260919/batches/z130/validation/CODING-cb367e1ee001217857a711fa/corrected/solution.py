import sys
queries=[]
for n in map(int,sys.stdin.buffer.read().split()):
 if n==0:break
 queries.append(n)
if not queries:raise SystemExit
limit=max(queries);ways=[1]*(limit+1);answer=[0]*(limit+1);answer[1]=1
for size in range(2,limit+1):
 count=ways[size];answer[size]=2*count;old=ways[:];factor=1
 for number in range(1,limit//size+1):
  factor=factor*(count+number-1)//number;shift=number*size
  for total in range(shift,limit+1):ways[total]+=old[total-shift]*factor
print('\n'.join(str(answer[n]) for n in queries))
