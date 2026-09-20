import sys
lines=sys.stdin.read().split();board=[];out=[]
def solve(board):
 masks=[sum(1<<i for i,c in enumerate(row) if c=='#') for row in board];n=len(masks);cover=[0]*(1<<n);answer=n
 for kept in range(1<<n):
  if kept:bit=kept&-kept;cover[kept]=cover[kept^bit]|masks[bit.bit_length()-1]
  answer=min(answer,max(n-kept.bit_count(),cover[kept].bit_count()))
 return answer
for line in lines:
 if line=='END':
  if board:out.append(str(solve(board)));board=[]
 else:
  board.append(line)
  if len(board)==15:out.append(str(solve(board)));board=[]
if board:out.append(str(solve(board)))
print('\n'.join(out))
