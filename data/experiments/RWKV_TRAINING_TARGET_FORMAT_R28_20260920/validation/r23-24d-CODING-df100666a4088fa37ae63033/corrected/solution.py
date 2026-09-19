import sys
v=iter(sys.stdin.read().split());n=int(next(v));q=int(next(v));rows=set();cols=set();row_sum=col_sum=n*(n+1)//2;row_count=col_count=n;out=[]
for _ in range(q):
 op=next(v);x=int(next(v))
 if op=='R':
  if x in rows:out.append('0')
  else:out.append(str(x*col_count+col_sum));rows.add(x);row_count-=1;row_sum-=x
 else:
  if x in cols:out.append('0')
  else:out.append(str(x*row_count+row_sum));cols.add(x);col_count-=1;col_sum-=x
print('\n'.join(out))
