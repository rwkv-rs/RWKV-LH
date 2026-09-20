import sys
def play(rows):
 columns=[[rows[r][c] for r in range(9,-1,-1)] for c in range(15)];moves=[];score=0
 while True:
  seen=set();best=[];anchor=None;color=None
  for c,column in enumerate(columns):
   for r,ch in enumerate(column):
    if (c,r) in seen:continue
    group=[(c,r)];seen.add((c,r))
    for x,y in group:
     for xx,yy in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
      if 0<=xx<len(columns) and 0<=yy<len(columns[xx]) and columns[xx][yy]==ch and (xx,yy) not in seen:seen.add((xx,yy));group.append((xx,yy))
    if len(group)>len(best):best=group;anchor=(r+1,c+1);color=ch
  if len(best)<2:break
  points=(len(best)-2)**2;score+=points;moves.append(f'Move {len(moves)+1} at ({anchor[0]},{anchor[1]}): removed {len(best)} balls of color {color}, got {points} points.')
  removed=set(best);columns=[[ch for r,ch in enumerate(column) if (c,r) not in removed] for c,column in enumerate(columns)];columns=[col for col in columns if col]
 remaining=sum(map(len,columns))
 if remaining==0:score+=1000
 moves.append(f'Final score: {score}, with {remaining} balls remaining.')
 return moves
v=iter(sys.stdin.read().split());out=[]
for case in range(1,int(next(v))+1):
 rows=[next(v) for _ in range(10)];out.append(f'Game {case}:\n\n'+'\n'.join(play(rows)))
print('\n\n'.join(out))
