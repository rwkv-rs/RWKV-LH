import sys
placements=[]
def place(cols,down,up,path):
 row=len(path)
 if row==8:placements.append(tuple(path));return
 for col in range(8):
  a=1<<col;b=1<<(row+col);c=1<<(row-col+7)
  if not(cols&a or down&b or up&c):place(cols|a,down|b,up|c,path+[col])
place(0,0,0,[]);v=list(map(int,sys.stdin.buffer.read().split()));out=[]
for i in range(v[0]):
 board=v[1+64*i:65+64*i];out.append(str(max(sum(board[8*r+c] for r,c in enumerate(p)) for p in placements)))
print('\n'.join(out))
