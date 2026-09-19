import sys
lines=sys.stdin.buffer;actions=int(lines.readline());stack=[];out=[]
for _ in range(actions):
 parts=lines.readline().split();value=int(parts[0])
 if value==-1:
  index=stack[-1][2];out.append(str(len(stack)-index-1)+' '+stack[index][1]);del stack[index:]
 elif value>0:
  best=len(stack) if not stack or value<=stack[stack[-1][2]][0] else stack[-1][2];stack.append((value,parts[1].decode(),best))
print('\n'.join(out))
