import sys
lines=sys.stdin.read().splitlines();n=int(lines[0]);pictures=[];at=1
for _ in range(n):
 while not lines[at]:at+=1
 pictures.append(lines[at:at+7]);at+=7
segments=[]
for col in (0,5,12,17):
 segments.extend([[(0,col+1),(0,col+2)],[(1,col+3),(2,col+3)],[(4,col+3),(5,col+3)],[(6,col+1),(6,col+2)],[(4,col),(5,col)],[(1,col),(2,col)],[(3,col+1),(3,col+2)]])
segments.extend([[(2,10)],[(4,10)]]);digit=['abcdef','bc','abdeg','abcdg','bcfg','acdfg','acdefg','abc','abcdefg','abcdfg'];masks=[sum(1<<(ord(c)-97) for c in word) for word in digit];expected=[0]*30
for minute in range(1440):
 hour,part=divmod(minute,60);nums=[hour//10 if hour>=10 else -1,hour%10,part//10,part%10];mask=(3<<28)
 for place,num in enumerate(nums):
  if num>=0:mask|=masks[num]<<(7*place)
 for j in range(30):
  if mask>>j&1:expected[j]|=1<<minute
expected=[x|(x<<1440) for x in expected];observed=[];full=(1<<n)-1
for cells in segments:
 r,c=cells[0];observed.append(sum((picture[r][c]=='X')<<i for i,picture in enumerate(pictures)))
possible=[0]*30;valid=False
for start in range(1440):
 statuses=[]
 for j,seen in enumerate(observed):
  normal=(expected[j]>>start)&full;choices=(1 if seen==0 else 2 if seen==full else 0)|(4 if seen==normal else 0)
  if not choices:break
  statuses.append(choices)
 else:
  valid=True
  for j,choices in enumerate(statuses):possible[j]|=choices
if not valid:print('impossible')
else:
 board=[['.']*21 for _ in range(7)]
 for cells,status in zip(segments,possible):
  char={1:'0',2:'1',4:'W'}.get(status,'?')
  for r,c in cells:board[r][c]=char
 print('\n'.join(''.join(row) for row in board))
