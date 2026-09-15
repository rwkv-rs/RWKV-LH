import sys,math
r,c,x,y,d,l=map(int,sys.stdin.buffer.read().split());mod=10**9+7;ans=0
for mask in range(16):
    rows=set();cols=set()
    if mask&1:rows.add(0)
    if mask&2:rows.add(x-1)
    if mask&4:cols.add(0)
    if mask&8:cols.add(y-1)
    cells=(x-len(rows))*(y-len(cols))
    if cells<d+l:continue
    ways=math.comb(cells,d+l)*math.comb(d+l,d)
    ans+=-ways if mask.bit_count()%2 else ways
print(ans*(r-x+1)*(c-y+1)%mod)
