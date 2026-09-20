import sys
def solve(grid,H,W):
 if W>H:grid=[list(row) for row in zip(*grid)];H,W=W,H
 empty=(0,)*(W+1);dp={(empty,0):0}
 def canonical(a):
  table={};out=[]
  for x in a:
   if x>0:
    if x not in table:table[x]=len(table)+1
    x=table[x]
   out.append(x)
  return tuple(out)
 for r in range(H):
  for c in range(W):
   cell=grid[r][c];new={};right=c+1<W and grid[r][c+1]!=1;down=r+1<H and grid[r+1][c]!=1
   for (state,finished),cost in dp.items():
    left=state[0];up=state[c+1];incoming=int(left!=0)+int(up!=0);a=list(state);a[0]=a[c+1]=0
    def put(a,finished,value):
     key=(canonical(a),finished)
     if value<new.get(key,10**9):new[key]=value
    if cell==1:
     if incoming==0:put(a,finished,cost)
     continue
    if cell in (2,3):
     bit=1<<(cell-2)
     if finished&bit or incoming>1:continue
     if incoming==0:
      if right:b=a.copy();b[0]=-cell;put(b,finished,cost+1)
      if down:b=a.copy();b[c+1]=-cell;put(b,finished,cost+1)
     else:
      label=left or up
      if label==-cell:put(a,finished|bit,cost)
      elif label>0:put([-cell if x==label else x for x in a],finished,cost)
     continue
    if incoming==0:
     put(a,finished,cost)
     if right and down:
      label=max(state)+1;a[0]=a[c+1]=label;put(a,finished,cost+2)
    elif incoming==1:
     label=left or up
     if right:b=a.copy();b[0]=label;put(b,finished,cost+1)
     if down:b=a.copy();b[c+1]=label;put(b,finished,cost+1)
    elif left>0 and up>0:
     if left!=up:put([left if x==up else x for x in a],finished,cost)
    elif left<0 and up<0:
     if left==up:put(a,finished|(1<<(-left-2)),cost)
    else:
     positive=max(left,up);negative=min(left,up);put([negative if x==positive else x for x in a],finished,cost)
   dp=new
 return dp.get((empty,3),0)
v=iter(map(int,sys.stdin.buffer.read().split()));out=[]
for H in v:
 W=next(v)
 if H==W==0:break
 grid=[[next(v) for _ in range(W)] for _ in range(H)];out.append(str(solve(grid,H,W)))
print('\n'.join(out))
