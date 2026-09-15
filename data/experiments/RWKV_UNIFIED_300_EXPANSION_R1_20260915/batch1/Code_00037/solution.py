import math
s=input().strip();t=input().strip();n=len(s);m=len(t)
a=t+'#'+(s*((n+m+n-1)//n))[:n+m-1];z=[0]*len(a);l=r=0
for i in range(1,len(a)):
    if i<=r:z[i]=min(r-i+1,z[i-l])
    while i+z[i]<len(a) and a[z[i]]==a[i+z[i]]:z[i]+=1
    if i+z[i]-1>r:l,r=i,i+z[i]-1
ok=[z[m+1+i]>=m for i in range(n)];ans=0
for start in range(math.gcd(n,m)):
    cycle=[];p=start
    while True:
        cycle.append(ok[p]);p=(p+m)%n
        if p==start:break
    if all(cycle):print(-1);raise SystemExit
    run=0
    for v in cycle+cycle:
        run=run+1 if v else 0;ans=max(ans,run)
print(ans)
