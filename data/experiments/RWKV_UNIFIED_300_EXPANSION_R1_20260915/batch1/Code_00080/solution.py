n,k=map(int,input().split());mod=10**9+7;hi=[];width=[];l=1
while l<=n:
    r=n//(n//l);hi.append(r);width.append(r-l+1);l=r+1
index={v:i for i,v in enumerate(hi)};dest=[index[n//v] for v in hi];dp=[1]*len(hi)
for _ in range(k-1):
    acc=0;pref=[]
    for v,w in zip(dp,width):acc=(acc+v*w)%mod;pref.append(acc)
    dp=[pref[j] for j in dest]
print(sum(v*w for v,w in zip(dp,width))%mod)
