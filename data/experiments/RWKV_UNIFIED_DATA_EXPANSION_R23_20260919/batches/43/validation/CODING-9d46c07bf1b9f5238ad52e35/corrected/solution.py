import sys
v=list(map(int,sys.stdin.buffer.read().split()));out=[]
for case,m in enumerate(v[1:1+v[0]],1):
 if m==1:out.append(f'Case {case}: 1');continue
 a,b=0,1;seq=[]
 while True:
  seq.append(a);a,b=b,(a+b)%m
  if a==0 and b==1:break
 maximum=max(seq);start=seq.index(maximum);rot=seq[start+1:]+seq[:start+1];stack=[];answer=0
 for x in reversed(rot):
  while stack and stack[-1][0]<=x:stack.pop()
  length=1+(stack[-1][1] if stack else 0);answer+=length;stack.append((x,length))
 out.append(f'Case {case}: {answer}')
print('\n'.join(out))
