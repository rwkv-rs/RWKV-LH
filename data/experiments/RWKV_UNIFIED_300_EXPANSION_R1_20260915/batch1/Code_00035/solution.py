n,m=map(int,input().split());s=input().strip();p=n;steps=[]
while p:
    q=max(0,p-m)
    while q<p and s[q]=='1':q+=1
    if q==p:print(-1);raise SystemExit
    steps.append(p-q);p=q
print(*reversed(steps))
