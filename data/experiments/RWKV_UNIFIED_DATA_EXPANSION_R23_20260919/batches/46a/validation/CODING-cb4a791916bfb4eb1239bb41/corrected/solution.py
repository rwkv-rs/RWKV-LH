import sys
v=sys.stdin.buffer.read().split();h,w,n=map(int,v[:3]);a=[x.decode() for x in v[3:]];MOD=998244353
def transitions(board,rows,cols):
 single=[[0]*10 for _ in range(rows)]
 for r in range(rows):
  for c in range(cols):single[r][int(board[r][c])]|=1<<c
 table=[[0]*10 for _ in range(1<<rows)]
 for mask in range(1,1<<rows):
  bit=mask&-mask;row=single[bit.bit_length()-1];old=table[mask^bit];table[mask]=[old[d]|row[d] for d in range(10)]
 return table
row_to_col=transitions(a,h,w);col_to_row=transitions(list(zip(*a)),w,h);dp=[0]*(1<<h);dp[-1]=1
for _ in range(n):
 for table,size in ((row_to_col,1<<w),(col_to_row,1<<h)):
  nxt=[0]*size
  for mask,count in enumerate(dp):
   if count:
    for target in table[mask][1:]:
     if target:nxt[target]=(nxt[target]+count)%MOD
  dp=nxt
print(sum(dp)%MOD)
