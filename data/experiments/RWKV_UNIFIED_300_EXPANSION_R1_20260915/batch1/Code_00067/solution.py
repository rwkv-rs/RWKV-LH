import sys
a=iter(map(int,sys.stdin.buffer.read().split()));n=next(a);p=[(next(a),next(a),next(a)) for _ in range(n)]
c=[[abs(x-u)+abs(y-v)+max(0,w-z) for u,v,w in p] for x,y,z in p];inf=10**30;size=1<<(n-1)
dp=[[inf]*n for _ in range(size)];dp[0][0]=0
for mask in range(size):
    remaining=(size-1)^mask
    for i,base in enumerate(dp[mask]):
        if base==inf:continue
        bits=remaining
        while bits:
            bit=bits&-bits;j=bit.bit_length();bits-=bit
            nxt=mask|bit;v=base+c[i][j]
            if v<dp[nxt][j]:dp[nxt][j]=v
print(min(dp[-1][i]+c[i][0] for i in range(1,n)))
