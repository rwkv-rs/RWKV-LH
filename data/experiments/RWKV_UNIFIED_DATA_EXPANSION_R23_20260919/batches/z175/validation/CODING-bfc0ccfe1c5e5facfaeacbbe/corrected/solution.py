import sys,math
values=iter(map(int,sys.stdin.buffer.read().split()));output=[]
for x in values:
 y=next(values);tx=next(values);ty=next(values);dx=tx-x;dy=ty-y;sx=(dx>0)-(dx<0);sy=(dy>0)-(dy<0);ax=abs(dx);ay=abs(dy);moves=[]
 if dx and dy:
  length=min(ax,ay);name=('N' if sy>0 else 'S')+('E' if sx>0 else 'W');moves.append((name,sx*length,sy*length,length*math.sqrt(2)))
 if ax>ay:moves.append(('E' if sx>0 else 'W',sx*(ax-ay),0,ax-ay))
 elif ay>ax:moves.append(('N' if sy>0 else 'S',0,sy*(ay-ax),ay-ax))
 moves.sort();output.append(str(len(moves)+1 if moves else 0));distance=0
 for name,mx,my,length in moves:
  output.append(f'{x:.2f} {y:.2f} {name}');x+=mx;y+=my;distance+=length
 if moves:output.append(f'{x:.2f} {y:.2f} X')
 output.extend([f'{distance:.3f}',''])
print('\n'.join(output))
