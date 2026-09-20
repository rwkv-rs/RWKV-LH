import sys
expression=sys.stdin.buffer.read().strip();left=[-1]*4;right=[-1]*4;names={66:0,67:1,75:2,73:3};arity=[3,3,2,1]
def application(a,b):
 left.append(a);right.append(b);return len(left)-1
current=None;contexts=[]
for char in expression:
 if char==40:contexts.append(current);current=None
 elif char==41:
  previous=contexts.pop()
  if previous is not None:current=application(previous,current)
 else:
  leaf=names[char];current=leaf if current is None else application(current,leaf)
work=[current];reductions=0
while work:
 head=work.pop();arguments=[]
 while True:
  while head>=4:arguments.append(right[head]);head=left[head]
  if len(arguments)<arity[head]:work.extend(arguments);break
  reductions+=1
  if head==3:head=arguments.pop()
  elif head==2:head=arguments.pop();arguments.pop()
  else:
   x=arguments.pop();y=arguments.pop();z=arguments.pop()
   if head==0:arguments.append(application(y,z))
   else:arguments.extend((y,z))
   head=x
print(reductions)
