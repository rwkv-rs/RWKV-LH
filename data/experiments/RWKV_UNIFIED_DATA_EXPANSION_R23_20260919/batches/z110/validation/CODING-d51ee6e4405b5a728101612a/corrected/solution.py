import sys,collections
f=sys.stdin;out=[];board_number=0
while True:
 header=f.readline()
 if not header:break
 if not header.strip():continue
 w,h=map(int,header.split())
 if w==h==0:break
 width=w+2;height=h+2;board=[' '*width]
 for _ in range(h):board.append(' '+f.readline().rstrip('\r\n').ljust(w)+' ')
 board.append(' '*width);board_number+=1;out.append(f'Board #{board_number}:');pair=0
 while True:
  line=f.readline()
  if not line:break
  if not line.strip():continue
  x1,y1,x2,y2=map(int,line.split())
  if x1==y1==x2==y2==0:break
  pair+=1;distance=[10**9]*(width*height*4);queue=collections.deque();start=(y1*width+x1)*4;target=y2*width+x2
  for d in range(4):distance[start+d]=0;queue.append((x1,y1,d))
  answer=None;directions=((1,0),(-1,0),(0,1),(0,-1))
  while queue:
   x,y,old=queue.popleft();cost=distance[(y*width+x)*4+old]
   if y*width+x==target:answer=cost+1;break
   for d,(dx,dy) in enumerate(directions):
    xx=x+dx;yy=y+dy
    if not (0<=xx<width and 0<=yy<height):continue
    if board[yy][xx]=='X' and (xx!=x2 or yy!=y2):continue
    index=(yy*width+xx)*4+d;value=cost+(d!=old)
    if value<distance[index]:
     distance[index]=value
     if d==old:queue.appendleft((xx,yy,d))
     else:queue.append((xx,yy,d))
  out.append(f'Pair {pair}: '+('impossible.' if answer is None else f'{answer} segments.'))
 out.append('')
print('\n'.join(out))
