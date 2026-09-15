from functools import lru_cache
L,R=map(int,input().split());mod=10**9+7
@lru_cache(None)
def f(bit,above,below,started):
    if bit<0:return int(started)
    lb=(L>>bit)&1;rb=(R>>bit)&1;ans=0
    for x,y in ((0,0),(0,1),(1,1)):
        if not started and x!=y:continue
        if not above and x<lb:continue
        if not below and y>rb:continue
        ans+=f(bit-1,above or x>lb,below or y<rb,started or x==1)
    return ans%mod
print(f(59,False,False,False))
