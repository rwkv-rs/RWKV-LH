import sys
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];people=[tuple(v[1+2*i:3+2*i]) for i in range(n)];answer=10**30;maximum=max(max(p) for p in people)
for height in range(1,maximum+1):
 width=0;forced=0;savings=[];possible=True
 for w,h in people:
  if h>height:
   if w>height:possible=False;break
   forced+=1;width+=h
  else:
   width+=w
   if w<=height and h<w:savings.append(w-h)
 if possible and forced<=n//2:
  savings.sort(reverse=True);width-=sum(savings[:n//2-forced]);answer=min(answer,width*height)
print(answer)
