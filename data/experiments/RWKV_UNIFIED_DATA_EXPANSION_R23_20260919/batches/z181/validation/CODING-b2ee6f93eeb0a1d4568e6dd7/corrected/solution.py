import sys
v=iter(sys.stdin.buffer.read().split());width=int(next(v));depth=int(next(v));height=int(next(v));cells=set()
for z in range(height):
 for y in range(depth):
  for x,char in enumerate(next(v)):
   if char==120:cells.add((x,y,z))
start=next(iter(cells));frames={start:(1,2,3,4)};stack=[start];normals=set()
while stack:
 cell=stack.pop();frame=frames[cell];normals.add(frame[3])
 for axis in range(3):
  for sign in (-1,1):
   neighbor=list(cell);neighbor[axis]+=sign;neighbor=tuple(neighbor)
   if neighbor in cells and neighbor not in frames:
    new=list(frame);new[3]=sign*frame[axis];new[axis]=-sign*frame[3];frames[neighbor]=tuple(new);stack.append(neighbor)
print('Yes' if len(normals)==8 else 'No')
