import sys
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];a=v[1:];original=[];zeros=0
for x in a:
 if x:original.append(zeros)
 else:zeros+=1
ones=len(original);limit=n*(n-1)//2;INF=10**9
if not ones or not zeros:print(' '.join(['0']*(limit+1)));raise SystemExit
maximum=ones*zeros;dp=[[INF]*(zeros+1)];dp[0][0]=0
for initial in original:
 newlimit=min(maximum,len(dp)-1+max(initial,zeros-initial));new=[[INF]*(zeros+1) for _ in range(newlimit+1)]
 for budget,row in enumerate(dp):
  hull=[];head=0
  for z,value in enumerate(row):
   if value<INF:
    intercept=2*value+z*z+z
    while len(hull)-head>=2:
     t1,b1=hull[-2];t2,b2=hull[-1]
     if (b2-b1)*(z-t2)>=(intercept-b2)*(t2-t1):hull.pop()
     else:break
    hull.append((z,intercept))
   if len(hull)==head:continue
   while len(hull)-head>=2 and hull[head+1][1]-2*hull[head+1][0]*z<=hull[head][1]-2*hull[head][0]*z:head+=1
   t,b=hull[head];bad=(b-2*t*z+z*z-z)//2;cost=budget+abs(z-initial)
   if cost<=newlimit and bad<new[cost][z]:new[cost][z]=bad
 dp=new
best=[INF]*(maximum+1)
for budget,row in enumerate(dp):best[budget]=min(value+(zeros-z)*(zeros-z-1)//2 for z,value in enumerate(row))
total=zeros*(zeros-1)//2;current=INF;out=[]
for budget in range(limit+1):
 if budget<=maximum:current=min(current,best[budget])
 out.append(str(total-current))
print(' '.join(out))
