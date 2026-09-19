import sys
v=list(map(int,sys.stdin.read().split()));out=[]
for i in range(0,len(v),3):
 d,r,t=v[i:i+3];age=4
 while True:
  sister=age*(age+1)//2-6;brother=max(0,(age-d)*(age-d+1)//2-3) if age-d>=3 else 0
  if sister+brother==r+t:out.append(str(r-sister));break
  if sister+brother>r+t:raise ValueError('inconsistent candle totals')
  age+=1
print('\n'.join(out))
